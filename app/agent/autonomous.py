"""Genuinely autonomous planner: an LLM decides each next SPL from the last result.

Unlike ScriptedPlanner/BotsV3Planner (fixed plans), this asks the LLM, step by step,
what to query next given everything seen so far — a real ReAct loop. The agent loop
(TriageAgent) drives it, enforces guardrails, validates each query via the Splunk MCP
server, runs it, and feeds the rows back here for the next decision.

Returns ONE action per `decide()` call:
  {"thought": str, "action": "search", "spl": str}
  {"thought": str, "action": "verdict", "severity": ..., "confidence": ...,
   "mitre": [["Txxxx","name"]], "narrative": str, "recommended_action": str}
"""
from __future__ import annotations

import json

from app.agent.llm import OpenAICompatLLM, extract_json, LLMError

_SYSTEM = """You are SentinelLoop, an autonomous SOC tier-1 analyst investigating a \
security alert using Splunk (the BOTS v3 dataset). You decide ONE next step at a time.

Tools you can take, returned as a single JSON object and nothing else:
- To run a search:  {"thought":"why","action":"search","spl":"search index=botsv3 ..."}
- To conclude:      {"thought":"why","action":"verdict","severity":"CRITICAL|HIGH|MEDIUM|LOW",
                     "confidence":0.0-1.0,"mitre":[["T1059.001","PowerShell"]],
                     "narrative":"plain-English what happened","recommended_action":"what to do"}

Rules:
- READ-ONLY SPL only. Every search MUST start with `search index=botsv3` and must NOT use
  delete/outputlookup/collect/sendemail/script/rest or any writing command.
- Investigate in 2-4 searches, then return a verdict. Decide the next query from the
  results you already have. Map findings to MITRE ATT&CK technique IDs.

What the data contains (use these real fields):
- sourcetype=wineventlog:security EventCode=4688 -> process creation. Fields:
  host, New_Process_Name, Creator_Process_Name, Process_Command_Line, Account_Name.
  (Encoded PowerShell shows Process_Command_Line=*-enc*.)
- sourcetype=wineventlog:security EventCode=4624 -> successful logons (host, Account_Name).
- sourcetype=aws:cloudtrail -> eventName, userIdentity.arn.
- Splunk has native ML: append `| anomalydetection action=annotate` to a stats search to
  flag statistical outliers (use this at least once to leverage Splunk's own AI).
Prefer `| stats ... by ...` and `| table ...`. Keep results small with `| head`.
Respond with ONLY the JSON object."""


class AutonomousPlanner:
    autonomous = True

    def __init__(self, llm: OpenAICompatLLM):
        self.llm = llm

    @property
    def model_name(self) -> str:
        return self.llm.model

    def decide(self, alert, history: list[dict], remaining: int = 3,
               force_verdict: bool = False) -> dict:
        msgs = [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": self._prompt(alert, history, remaining, force_verdict)},
        ]
        raw = self.llm.chat(msgs)
        action = extract_json(raw)
        if "action" not in action:
            raise LLMError("LLM action missing 'action' field")
        return action

    def _prompt(self, alert, history: list[dict], remaining: int, force_verdict: bool) -> str:
        lines = [
            f"ALERT {alert.id}: {alert.title}",
            f"host={alert.host}  severity={alert.severity.value}  source={alert.source}",
            f"summary: {alert.summary}",
        ]
        if alert.raw.get("user"):
            lines.append(f"user: {alert.raw['user']}")
        if not history:
            lines.append("\nNo searches run yet. Decide your first search.")
        else:
            lines.append("\nInvestigation so far:")
            for i, h in enumerate(history, 1):
                if h.get("error"):
                    lines.append(f"  [{i}] SPL: {h['spl']}\n      ERROR/blocked: {h['error']}")
                else:
                    preview = json.dumps(h.get("rows", [])[:5])[:600]
                    lines.append(f"  [{i}] SPL: {h['spl']}\n"
                                 f"      {h.get('row_count', 0)} rows; sample: {preview}")
        if force_verdict:
            lines.append("\nYou are OUT of search budget. Return ONLY a verdict JSON now "
                         "(action=verdict) with severity, confidence, mitre, narrative and "
                         "recommended_action based on the evidence above.")
        else:
            lines.append(f"\nYou have {remaining} search(es) left before you must conclude. "
                         "Prefer to conclude early: if you already have enough evidence, return "
                         "a verdict now (action=verdict). Otherwise decide the single most "
                         "useful next search.")
        return "\n".join(lines)
