"""The agentic triage loop: perceive -> reason -> act -> (self-heal) -> verify -> decide.

Two execution modes:
  - static    : a planner returns a fixed Plan (ScriptedPlanner / BotsV3Planner).
  - autonomous: an LLM planner decides each next SPL from the last result (ReAct).
                Guardrailed: read-only index=botsv3 allowlist, validate-before-execute
                via the Splunk MCP server, bounded steps, deterministic fallback.

Framework-agnostic: it emits StepEvent objects via a callback. The Qt worker wires
that callback to a signal so the UI can render the agent thinking live.
"""
from __future__ import annotations

import csv
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from app.core.models import Alert, StepEvent, StepKind, Verdict, Severity
from app.splunk.client import SchemaDriftError, FixtureSplunk

_AUDIT_CSV = Path("audit_log.csv")  # the "second alert action" — local CSV audit trail
_MAX_AUTO_STEPS = 5
# read-only guardrail: writing/dangerous SPL commands the agent may never run
_FORBIDDEN = re.compile(
    r"\|\s*(delete|outputlookup|outputcsv|collect|sendemail|sendalert|script|"
    r"runshellscript|rest|tscollect|mcollect|meventcollect|crawl)\b", re.IGNORECASE)


class TriageAgent:
    def __init__(self, splunk, planner, emit: Callable[[StepEvent], None] | None = None,
                 step_delay: float = 0.7, write_back: bool = True, audit_csv: bool = True):
        self.splunk = splunk
        self.planner = planner
        self.emit = emit or (lambda e: None)
        self.delay = step_delay
        self.write_back = write_back
        self.audit_csv = audit_csv

    def _step(self, ev: StepEvent) -> None:
        self.emit(ev)
        if self.delay:
            time.sleep(self.delay)

    def investigate(self, alert: Alert) -> Verdict:
        self._step(StepEvent(
            StepKind.THOUGHT, "Triage started",
            f"Picking up notable {alert.id} — {alert.title} on {alert.host}.",
        ))
        if getattr(self.planner, "autonomous", False):
            return self._investigate_autonomous(alert)
        return self._investigate_static(alert, self.planner)

    # ── static (fixed-plan) mode ─────────────────────────────────────────
    def _investigate_static(self, alert: Alert, planner) -> Verdict:
        plan = planner.plan(alert)
        timeline: list[tuple[str, str]] = []
        for i, step in enumerate(plan.steps, 1):
            self._step(StepEvent(StepKind.THOUGHT, f"Step {i}: reasoning", step.thought))
            rows = self._run_with_heal(step)
            self._step(StepEvent(StepKind.RESULT, step.result_caption or f"{len(rows)} result(s)",
                                 f"{len(rows)} row(s) returned.", rows=rows[:20]))
            if rows:
                timeline.append((rows[0].get("_time", ""), step.result_caption or "finding"))
            if step.correlate:
                self._step(StepEvent(StepKind.CORRELATE, "Correlating", step.correlate))

        self._step(StepEvent(StepKind.CONCLUSION, "Verdict",
                             f"Severity {plan.severity} at {int(plan.confidence*100)}% confidence."))
        verdict = Verdict(
            alert_id=alert.id, severity=Severity(plan.severity), confidence=plan.confidence,
            mitre=plan.mitre, narrative=plan.narrative, timeline=timeline,
            recommended_action=plan.recommended_action,
        )
        self._finalize(alert, verdict)
        return verdict

    # ── autonomous (LLM ReAct) mode ──────────────────────────────────────
    def _investigate_autonomous(self, alert: Alert) -> Verdict:
        history: list[dict] = []
        timeline: list[tuple[str, str]] = []
        verdict: Verdict | None = None

        for i in range(_MAX_AUTO_STEPS):
            remaining = _MAX_AUTO_STEPS - i - 1
            try:
                action = self.planner.decide(alert, history, remaining)
            except Exception as exc:  # LLM unreachable/garbled -> deterministic fallback
                self._step(StepEvent(StepKind.ERROR, "LLM unavailable — falling back",
                                     f"{str(exc)[:140]} Switching to the deterministic planner."))
                return self._investigate_static(alert, self._fallback_planner())

            thought = (action.get("thought") or "").strip()
            if thought:
                self._step(StepEvent(StepKind.THOUGHT, f"Step {i + 1}: reasoning", thought))

            if action.get("action") == "verdict":
                verdict = self._verdict_from_action(alert, action, timeline)
                break

            spl = (action.get("spl") or "").strip()
            if not spl:
                history.append({"spl": "(none)", "error": "no SPL provided"})
                continue

            self._step(StepEvent(StepKind.SPL, "Running SPL", "", spl=spl))
            ok, reason = self._guard(spl)
            if not ok:
                self._step(StepEvent(StepKind.ERROR, "Query blocked by guardrail", reason))
                history.append({"spl": spl, "error": f"blocked: {reason}"})
                continue
            self._validate(spl)  # validate-before-execute via the Splunk MCP server

            try:
                rows = self.splunk.run_spl(spl)
            except Exception as exc:  # surface, let the agent adapt next step
                self._step(StepEvent(StepKind.ERROR, "Search error", str(exc)[:160]))
                history.append({"spl": spl, "error": str(exc)[:160]})
                continue

            self._step(StepEvent(StepKind.RESULT, f"{len(rows)} result(s)",
                                 f"{len(rows)} row(s) returned.", rows=rows[:20]))
            if rows:
                timeline.append((rows[0].get("_time", ""), "finding"))
            history.append({"spl": spl, "row_count": len(rows), "rows": rows[:8]})

        if verdict is None:
            # Out of search budget — ask the LLM for a final verdict from the evidence.
            try:
                action = self.planner.decide(alert, history, 0, force_verdict=True)
                if action.get("action") == "verdict":
                    verdict = self._verdict_from_action(alert, action, timeline)
            except Exception:
                verdict = None
            if verdict is None:
                verdict = self._verdict_from_action(alert, self._synth_verdict(alert), timeline)
            self._step(StepEvent(StepKind.CONCLUSION, "Verdict",
                                 f"Severity {verdict.severity.value} at "
                                 f"{int(verdict.confidence*100)}% confidence."))
        else:
            self._step(StepEvent(StepKind.CONCLUSION, "Verdict",
                                 f"Severity {verdict.severity.value} at "
                                 f"{int(verdict.confidence*100)}% confidence."))
        self._finalize(alert, verdict)
        return verdict

    def _guard(self, spl: str) -> tuple[bool, str]:
        low = spl.lower()
        if "index=botsv3" not in low:
            return False, "must target index=botsv3"
        if _FORBIDDEN.search(spl):
            return False, "writing/dangerous command not allowed (read-only)"
        return True, ""

    def _validate(self, spl: str) -> None:
        """Validate the SPL via the Splunk MCP server's validate_spl tool, if available."""
        fn = getattr(self.splunk, "validate_spl", None)
        if not callable(fn):
            return
        try:
            msg = fn(spl)
        except Exception:
            msg = None
        if msg:
            clean = " ".join(str(msg).split())  # flatten newlines
            self._step(StepEvent(StepKind.CORRELATE, "Validated via Splunk MCP", clean[:160]))

    def _verdict_from_action(self, alert: Alert, action: dict,
                             timeline: list[tuple[str, str]]) -> Verdict:
        sev = str(action.get("severity", "MEDIUM")).upper()
        if sev not in Severity.__members__:
            sev = "MEDIUM"
        try:
            conf = max(0.0, min(1.0, float(action.get("confidence", 0.6))))
        except (TypeError, ValueError):
            conf = 0.6
        mitre: list[tuple[str, str]] = []
        for m in action.get("mitre", []) or []:
            if isinstance(m, (list, tuple)) and len(m) >= 2:
                mitre.append((str(m[0]), str(m[1])))
            elif isinstance(m, str):
                mitre.append((m, ""))
        return Verdict(
            alert_id=alert.id, severity=Severity[sev], confidence=conf, mitre=mitre,
            narrative=str(action.get("narrative", "")).strip(), timeline=timeline,
            recommended_action=str(action.get("recommended_action", "")).strip(),
        )

    def _synth_verdict(self, alert: Alert) -> dict:
        return {
            "severity": alert.severity.value, "confidence": 0.6, "mitre": [],
            "narrative": f"Autonomous triage of '{alert.title}' on {alert.host} reached its "
                         "step budget; escalate for analyst review.",
            "recommended_action": "Escalate to a tier-2 analyst with the gathered evidence.",
        }

    def _fallback_planner(self):
        from app.agent.botsv3_planner import BotsV3Planner
        from app.agent.planner import ScriptedPlanner
        return ScriptedPlanner() if isinstance(self.splunk, FixtureSplunk) else BotsV3Planner()

    # ── shared: schema-drift self-heal (static mode) ─────────────────────
    def _run_with_heal(self, step) -> list[dict]:
        self._step(StepEvent(StepKind.SPL, "Running SPL", "", spl=step.spl))
        try:
            rows = self.splunk.run_spl(step.spl, fixture=step.fixture)
        except SchemaDriftError as drift:
            return self._heal(step, drift.missing_field)
        if step.drift_field and step.healed_spl and not rows:
            return self._heal(step, step.drift_field)
        return rows

    def _heal(self, step, missing_field: str) -> list[dict]:
        self._step(StepEvent(
            StepKind.DRIFT, "Schema drift detected",
            f"Field '{missing_field}' isn't present on this sourcetype — the saved "
            "search silently returns nothing (exactly how brittle dashboards break). "
            "Rewriting to the current field…",
        ))
        healed = step.healed_spl
        if not healed and hasattr(self.planner, "heal_spl"):
            healed = self.planner.heal_spl(step.spl, missing_field)
        healed = healed or step.spl
        self._step(StepEvent(StepKind.HEAL, "Self-healed query", spl=healed,
                             body="Re-issuing the corrected search."))
        return self.splunk.run_spl(healed, fixture=step.fixture)

    # ── shared: act on the verdict (CSV audit + Splunk write-back) ───────
    def _finalize(self, alert: Alert, verdict: Verdict) -> None:
        actions: list[str] = []
        if self.audit_csv:
            try:
                self._write_audit(alert, verdict)
                actions.append("Audit record appended to audit_log.csv")
            except Exception:
                pass
        if self.write_back and self.splunk.post_annotation(
                alert.id, f"SentinelLoop verdict: {verdict.severity.value} "
                          f"({int(verdict.confidence*100)}%)"):
            actions.append("Annotation written back to Splunk")
        verdict.actions_taken = actions
        for a in actions:
            self._step(StepEvent(StepKind.ACTION, "Action taken", a))

    def _write_audit(self, alert: Alert, verdict: Verdict) -> None:
        new = not _AUDIT_CSV.exists()
        with open(_AUDIT_CSV, "a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            if new:
                w.writerow(["timestamp", "alert_id", "host", "severity", "confidence",
                            "mitre", "recommended_action"])
            w.writerow([
                datetime.now(timezone.utc).isoformat(),
                alert.id, alert.host, verdict.severity.value, f"{verdict.confidence:.2f}",
                ";".join(m[0] for m in verdict.mitre), verdict.recommended_action,
            ])
