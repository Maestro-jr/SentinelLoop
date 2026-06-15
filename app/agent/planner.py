"""The agent's brain: decides what to investigate next.

Two planners behind one interface:
  - ScriptedPlanner : deterministic investigation plans (DEMO; reliable on stage)
  - LLMPlanner      : Claude generates the plan + heals SPL (LIVE, optional)

A plan is an ordered list of InvestigationStep. Each step carries the SPL we
display, the fixture that backs it in demo, and—critically—`drift` metadata so
the loop can demonstrate self-healing when a field has been renamed.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class InvestigationStep:
    thought: str
    spl: str
    fixture: str | None = None          # demo result backing this step
    result_caption: str = ""
    drift_field: str | None = None      # legacy field that triggers drift
    healed_spl: str | None = None       # the rewritten query after self-heal
    correlate: str = ""                 # optional correlation note after the result


@dataclass
class Plan:
    steps: list[InvestigationStep] = field(default_factory=list)
    severity: str = "MEDIUM"
    confidence: float = 0.6
    mitre: list = field(default_factory=list)
    narrative: str = ""
    recommended_action: str = ""


class ScriptedPlanner:
    """Hand-built, on-theme investigation plans. Powers the demo deterministically."""

    def plan(self, alert) -> Plan:
        host = alert.host
        # The headline beacon scenario gets the full, drift-healing investigation.
        if alert.id == "NTBL-4471":
            return Plan(
                steps=[
                    InvestigationStep(
                        thought=f"Alert names host {host} with encoded PowerShell from an "
                                "Office parent. First I need the full process tree to see "
                                "what the macro actually launched.",
                        # NOTE: uses the legacy field `process_name` -> triggers schema drift.
                        spl=(f'index=sysmon host={host} EventCode=1 '
                             f'| table _time, parent_process, process_name, command_line, user'),
                        fixture="search_process.json",
                        result_caption="3 processes — WINWORD → powershell → cmd/rundll32",
                        drift_field="process_name",
                        healed_spl=(f'index=sysmon host={host} EventCode=1 '
                                    f'| rename Processes.process as process '
                                    f'| table _time, parent_process, process, command_line, user'),
                        correlate="Classic macro-dropper chain: Office spawns PowerShell, "
                                  "which spawns living-off-the-land binaries (cmd, rundll32).",
                    ),
                    InvestigationStep(
                        thought="A dropper usually phones home. I'll pull outbound "
                                "connections from this host and check reputation + timing.",
                        spl=(f'index=network host={host} dest_port=443 '
                             f'| stats count, avg(interval_s) by dest_ip, reputation'),
                        fixture="search_network.json",
                        result_caption="Regular 60s beacon to 185.220.101.47 (rep: malicious)",
                        correlate="Fixed-interval outbound TLS to a malicious IP = C2 beacon, "
                                  "not user traffic.",
                    ),
                    InvestigationStep(
                        thought="Beacon confirmed. Now: did the operator move laterally? "
                                "Check this user's remote logons after the beacon started.",
                        spl=(f'index=auth user={alert.raw.get("user","")} logon_type=3 '
                             f'| table _time, src_host, dest_host, result'),
                        fixture="search_auth.json",
                        result_caption="One successful type-3 logon to FILE-SRV-02",
                        correlate="Successful lateral logon to a file server — staging for "
                                  "collection/exfil is likely the next move.",
                    ),
                ],
                severity="CRITICAL",
                confidence=0.86,
                mitre=[
                    ("T1566.001", "Phishing: Spearphishing Attachment"),
                    ("T1059.001", "Command and Scripting Interpreter: PowerShell"),
                    ("T1071.001", "Application Layer Protocol: Web Protocols (C2)"),
                    ("T1021.002", "Remote Services: SMB/Windows Admin Shares"),
                ],
                narrative=(
                    f"A malicious Office macro on {host} launched encoded PowerShell, which "
                    "dropped and executed a DLL via rundll32. The host then established a "
                    "regular 60-second C2 beacon to 185.220.101.47 (known-malicious). The "
                    "actor used the compromised account to make a successful lateral logon to "
                    "FILE-SRV-02, indicating an active, hands-on-keyboard intrusion moving "
                    "toward data collection."
                ),
                recommended_action=(
                    "Isolate FIN-WK-014, disable j.okafor, block 185.220.101.47 at the "
                    "perimeter, and hunt for the dropped DLL across the fleet."
                ),
            )

        # Generic fallback plan for the other alerts (keeps the app honest/usable).
        return Plan(
            steps=[
                InvestigationStep(
                    thought=f"Pull the raw events behind this notable on {host} to "
                            "establish what actually happened.",
                    spl=f'index=* host={host} | head 20 | table _time, source, _raw',
                    fixture=None,
                    result_caption="Context gathered",
                ),
            ],
            severity=alert.severity.value,
            confidence=0.55,
            mitre=[],
            narrative=f"Initial triage of '{alert.title}' on {host}. Insufficient "
                      "corroborating signal for a high-confidence verdict in this MVP scenario.",
            recommended_action="Escalate to a tier-2 analyst for manual review.",
        )


class LLMPlanner:
    """Claude-backed planner (optional). Falls back to scripted on any error.

    Wires Splunk AI usage in LIVE mode: Claude proposes the next SPL, and on a
    SchemaDriftError the loop calls heal_spl() to rewrite the query.
    """

    def __init__(self, api_key: str, model: str):
        self._model = model
        self._fallback = ScriptedPlanner()
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=api_key)
        except Exception:
            self._client = None

    _SYSTEM = (
        "You are an autonomous SOC tier-1 analyst that investigates security alerts "
        "using Splunk. Given an alert, produce a short investigation plan: an ordered "
        "list of 2-4 SPL searches, each with the reasoning behind it, plus a final "
        "verdict. Use Splunk Common Information Model field names. Respond with ONLY a "
        "JSON object, no prose, matching this schema:\n"
        '{"steps":[{"thought":str,"spl":str,"result_caption":str,"correlate":str}],'
        '"severity":"CRITICAL|HIGH|MEDIUM|LOW","confidence":0.0-1.0,'
        '"mitre":[["Txxxx","name"]],"narrative":str,"recommended_action":str}'
    )

    def plan(self, alert) -> Plan:
        """Ask Claude for a real investigation plan. Fall back to scripted on any error."""
        if not self._client:
            return self._fallback.plan(alert)
        try:
            import json
            prompt = (
                f"Alert ID: {alert.id}\nTitle: {alert.title}\nSeverity: {alert.severity.value}\n"
                f"Host: {alert.host}\nSource: {alert.source}\nSummary: {alert.summary}\n"
                f"Raw: {json.dumps(alert.raw)[:800]}"
            )
            msg = self._client.messages.create(
                model=self._model,
                max_tokens=1500,
                system=self._SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            text = msg.content[0].text.strip()
            start, end = text.find("{"), text.rfind("}")
            data = json.loads(text[start:end + 1])
            steps = [
                InvestigationStep(
                    thought=s.get("thought", ""),
                    spl=s.get("spl", ""),
                    fixture=None,                      # live: query Splunk for real
                    result_caption=s.get("result_caption", ""),
                    correlate=s.get("correlate", ""),
                )
                for s in data.get("steps", [])
            ]
            if not steps:
                return self._fallback.plan(alert)
            return Plan(
                steps=steps,
                severity=data.get("severity", alert.severity.value),
                confidence=float(data.get("confidence", 0.6)),
                mitre=[tuple(m) for m in data.get("mitre", [])],
                narrative=data.get("narrative", ""),
                recommended_action=data.get("recommended_action", ""),
            )
        except Exception:
            return self._fallback.plan(alert)

    def heal_spl(self, broken_spl: str, missing_field: str) -> str:
        """Ask Claude to rewrite a query whose field vanished. Best-effort."""
        if not self._client:
            return broken_spl.replace(missing_field, missing_field)
        try:
            msg = self._client.messages.create(
                model=self._model,
                max_tokens=400,
                messages=[{
                    "role": "user",
                    "content": (
                        "You are a Splunk SPL expert. The field "
                        f"'{missing_field}' no longer exists (schema drift). Rewrite this "
                        "search to use the current Common Information Model field and return "
                        f"ONLY the corrected SPL, no prose:\n\n{broken_spl}"
                    ),
                }],
            )
            return msg.content[0].text.strip()
        except Exception:
            return broken_spl
