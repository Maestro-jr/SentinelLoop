"""Investigation planner grounded in the real BOTS v3 dataset (LIVE mode).

Unlike the ScriptedPlanner (which backs the polished DEMO with fixtures), this
planner emits SPL that actually runs against `index=botsv3` on the user's Splunk.
The hero path ('ps_encoded') reproduces a real finding — an encoded PowerShell
download cradle on host ABUNGST-L — and demonstrates honest schema-drift healing:
the legacy query filters on `process_name` (absent on wineventlog:security, so it
returns 0 rows) and the agent heals to the correct `New_Process_Name` field.
"""
from __future__ import annotations

from app.agent.planner import Plan, InvestigationStep


class BotsV3Planner:
    def plan(self, alert) -> Plan:
        det = alert.raw.get("detection", "")
        if det == "ps_encoded":
            return self._ps_encoded(alert)
        if det in ("ps_exec", "recon"):
            return self._host_process_story(alert)
        return self._generic(alert)

    def _ps_encoded(self, alert) -> Plan:
        h = alert.host
        acct = alert.raw.get("user") or "the account"
        return Plan(
            steps=[
                InvestigationStep(
                    thought=(f"This alert flags encoded PowerShell on {h}. I'll pull the "
                             "process-creation events (4688) for that host. Note the legacy "
                             "saved search filters on the field 'process_name'."),
                    spl=(f"search index=botsv3 sourcetype=wineventlog:security EventCode=4688 "
                         f"host={h} process_name=*powershell* "
                         f"| table _time, Creator_Process_Name, New_Process_Name, Process_Command_Line, Account_Name"),
                    drift_field="process_name",
                    healed_spl=(f"search index=botsv3 sourcetype=wineventlog:security EventCode=4688 "
                                f"host={h} (New_Process_Name=*powershell* OR Process_Command_Line=*powershell*) "
                                f"| table _time, Creator_Process_Name, New_Process_Name, Process_Command_Line, Account_Name"),
                    result_caption="Encoded PowerShell command captured",
                    correlate=("The command runs powershell.exe -enc with a base64 payload that "
                               "decodes to an IEX download cradle (Net.WebClient.DownloadString over "
                               "a bit.ly redirect) — a classic stage-1 loader."),
                ),
                InvestigationStep(
                    thought=("What else ran on this host? Inventory its process creations to spot "
                             "follow-on tooling or living-off-the-land binaries."),
                    spl=(f"search index=botsv3 sourcetype=wineventlog:security EventCode=4688 host={h} "
                         f"| stats count by New_Process_Name | sort -count | head 12"),
                    result_caption="Process inventory for the host",
                    correlate="Recon/LOLBins alongside the cradle point to hands-on activity, not a one-off.",
                ),
                InvestigationStep(
                    thought="Finally, check successful logons on this host to gauge account usage.",
                    spl=(f"search index=botsv3 sourcetype=wineventlog:security EventCode=4624 host={h} "
                         f"| stats count by Account_Name | sort -count | head 8"),
                    result_caption="Successful logons by account",
                ),
            ],
            severity="HIGH",
            confidence=0.9,
            mitre=[
                ("T1059.001", "Command and Scripting Interpreter: PowerShell"),
                ("T1105", "Ingress Tool Transfer"),
                ("T1071.001", "Application Layer Protocol: Web Protocols"),
            ],
            narrative=(
                f"On {h}, {acct} executed an encoded PowerShell command that decodes to an IEX "
                "download cradle pulling a payload over HTTP (a bit.ly redirect). This is a stage-1 "
                "loader consistent with initial-access/execution activity in the BOTS v3 dataset."),
            recommended_action=(
                f"Isolate {h}, reset {acct}'s credentials, block the download URL at the proxy, and "
                "sweep the fleet for the second-stage payload."),
        )

    def _host_process_story(self, alert) -> Plan:
        h = alert.host
        return Plan(
            steps=[
                InvestigationStep(
                    thought=f"Establish what {h} has been executing — pull its process creations.",
                    spl=(f"search index=botsv3 sourcetype=wineventlog:security EventCode=4688 host={h} "
                         f"| stats count by New_Process_Name | sort -count | head 12"),
                    result_caption="Process inventory for the host",
                    correlate="Looking for interpreters, recon tools and LOLBins among the top processes.",
                ),
                InvestigationStep(
                    thought="Check successful logons to understand which accounts are active here.",
                    spl=(f"search index=botsv3 sourcetype=wineventlog:security EventCode=4624 host={h} "
                         f"| stats count by Account_Name | sort -count | head 8"),
                    result_caption="Successful logons by account",
                ),
            ],
            severity=alert.severity.value,
            confidence=0.66,
            mitre=[("T1059", "Command and Scripting Interpreter"), ("T1049", "System Network Connections Discovery")],
            narrative=(f"Triage of '{alert.title}' on {h} against BOTS v3: reviewed process "
                       "creation and logon activity to scope the behaviour."),
            recommended_action="Confirm whether the activity is sanctioned; escalate to tier-2 if not.",
        )

    def _generic(self, alert) -> Plan:
        h = alert.host
        return Plan(
            steps=[
                InvestigationStep(
                    thought=f"Pull recent events for {h} to establish context.",
                    spl=f"search index=botsv3 host={h} | head 20 | table _time, sourcetype, source",
                    result_caption="Context gathered",
                ),
            ],
            severity=alert.severity.value,
            confidence=0.6,
            mitre=[],
            narrative=f"Initial triage of '{alert.title}' on {h} against BOTS v3.",
            recommended_action="Escalate to tier-2 for manual review.",
        )
