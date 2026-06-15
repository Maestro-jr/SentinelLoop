"""Agent-loop tests — verify the self-heal beat and the verdict, no Qt needed."""
from __future__ import annotations

from app.core.models import StepKind, Severity
from app.splunk.client import FixtureSplunk
from app.agent.planner import ScriptedPlanner
from app.agent.loop import TriageAgent

# Tests pin the DEMO path (fixtures + ScriptedPlanner) so they stay deterministic
# regardless of whether a live .env is present.


def _run(alert_idx=0):
    splunk = FixtureSplunk()
    alerts = splunk.list_alerts()
    events = []
    agent = TriageAgent(splunk, ScriptedPlanner(), emit=events.append, step_delay=0)
    verdict = agent.investigate(alerts[alert_idx])
    return alerts[alert_idx], events, verdict


def test_alerts_load():
    alerts = FixtureSplunk().list_alerts()
    assert len(alerts) >= 3
    assert alerts[0].id == "NTBL-4471"


def test_self_heal_fires_on_beacon_alert():
    _, events, _ = _run(0)
    kinds = [e.kind for e in events]
    assert StepKind.DRIFT in kinds, "schema drift must be detected"
    assert StepKind.HEAL in kinds, "agent must self-heal the query"
    # heal must come after drift
    assert kinds.index(StepKind.HEAL) > kinds.index(StepKind.DRIFT)


def test_verdict_is_critical_with_mitre():
    _, _, verdict = _run(0)
    assert verdict.severity == Severity.CRITICAL
    assert verdict.confidence >= 0.8
    assert len(verdict.mitre) >= 3
    assert verdict.actions_taken, "should record audit + write-back actions"


def test_runs_produce_spl_and_results():
    _, events, _ = _run(0)
    assert any(e.kind == StepKind.SPL and e.spl for e in events)
    assert any(e.kind == StepKind.RESULT and e.rows for e in events)
