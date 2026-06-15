"""The agentic triage loop: perceive -> reason -> act -> (self-heal) -> verify -> decide.

Framework-agnostic: it emits StepEvent objects via a callback. The Qt worker wires
that callback to a signal so the UI can render the agent thinking live.
"""
from __future__ import annotations

import csv
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from app.core.models import Alert, StepEvent, StepKind, Verdict, Severity
from app.splunk.client import SchemaDriftError

_AUDIT_CSV = Path("audit_log.csv")  # the "second alert action" — local CSV audit trail


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
            StepKind.THOUGHT,
            "Triage started",
            f"Picking up notable {alert.id} — {alert.title} on {alert.host}.",
        ))

        plan = self.planner.plan(alert)
        timeline: list[tuple[str, str]] = []

        for i, step in enumerate(plan.steps, 1):
            self._step(StepEvent(StepKind.THOUGHT, f"Step {i}: reasoning", step.thought))
            rows = self._run_with_heal(step)

            self._step(StepEvent(
                StepKind.RESULT,
                step.result_caption or f"{len(rows)} result(s)",
                f"{len(rows)} row(s) returned.",
                rows=rows[:20],
            ))
            if rows:
                timeline.append((rows[0].get("_time", ""), step.result_caption or "finding"))
            if step.correlate:
                self._step(StepEvent(StepKind.CORRELATE, "Correlating", step.correlate))

        # Decide
        self._step(StepEvent(
            StepKind.CONCLUSION, "Verdict",
            f"Severity {plan.severity} at {int(plan.confidence*100)}% confidence.",
        ))

        verdict = Verdict(
            alert_id=alert.id,
            severity=Severity(plan.severity),
            confidence=plan.confidence,
            mitre=plan.mitre,
            narrative=plan.narrative,
            timeline=timeline,
            recommended_action=plan.recommended_action,
        )

        # Act: audit to CSV (second alert action) + write-back annotation to Splunk.
        actions: list[str] = []
        if self.audit_csv:
            try:
                self._write_audit(alert, verdict)
                actions.append("Audit record appended to audit_log.csv")
            except Exception:
                pass
        if self.write_back and self.splunk.post_annotation(
                alert.id, f"SentinelLoop verdict: {plan.severity} ({int(plan.confidence*100)}%)"):
            actions.append("Annotation written back to Splunk")
        verdict.actions_taken = actions
        for a in actions:
            self._step(StepEvent(StepKind.ACTION, "Action taken", a))

        return verdict

    def _run_with_heal(self, step) -> list[dict]:
        """Run a step's SPL; on schema drift, self-heal and retry once.

        Two drift signals are handled:
          - DEMO/fixtures raise SchemaDriftError (an explicit "unknown field").
          - LIVE Splunk silently returns 0 rows when a query filters on a field that
            no longer exists on the sourcetype — the real way drift breaks saved
            searches. If the step declares a drift_field + healed_spl and we get
            nothing back, we treat that as drift and heal.
        """
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

    def _write_audit(self, alert: Alert, verdict: Verdict) -> None:
        new = not _AUDIT_CSV.exists()
        with open(_AUDIT_CSV, "a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            if new:
                w.writerow(["timestamp", "alert_id", "host", "severity", "confidence",
                            "mitre", "recommended_action"])
            w.writerow([
                datetime.now(timezone.utc).isoformat(),
                alert.id, alert.host, verdict.severity.value,
                f"{verdict.confidence:.2f}",
                ";".join(m[0] for m in verdict.mitre),
                verdict.recommended_action,
            ])
