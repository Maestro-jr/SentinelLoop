"""Dataclasses that cross the UI <-> Agent <-> Splunk boundaries.

Keeping these dumb and serializable means the UI never imports agent internals
and the agent never imports Qt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

    @property
    def color(self) -> str:
        return {
            "CRITICAL": "#ff4d6d",
            "HIGH": "#ff9e00",
            "MEDIUM": "#ffd60a",
            "LOW": "#4dd4ac",
            "INFO": "#7b8cff",
        }[self.value]


@dataclass
class Alert:
    id: str
    title: str
    severity: Severity
    host: str
    source: str
    summary: str
    confidence: float = 0.0          # AI confidence 0..1
    tags: list[str] = field(default_factory=list)
    age: str = ""                    # human "2m ago"
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def impact(self) -> str:
        return {"CRITICAL": "Critical", "HIGH": "High", "MEDIUM": "Medium",
                "LOW": "Low", "INFO": "Info"}[self.severity.value]


class StepKind(str, Enum):
    THOUGHT = "THOUGHT"        # agent reasoning
    SPL = "SPL"               # a query it decided to run
    RESULT = "RESULT"         # rows / findings back from Splunk
    DRIFT = "DRIFT"           # schema-drift detected (a field vanished/renamed)
    HEAL = "HEAL"             # agent rewrote the SPL to self-heal
    CORRELATE = "CORRELATE"   # connecting findings
    CONCLUSION = "CONCLUSION"  # verdict reasoning
    ACTION = "ACTION"         # something the agent did (csv/write-back)
    ERROR = "ERROR"


@dataclass
class StepEvent:
    kind: StepKind
    title: str
    body: str = ""
    spl: str = ""
    rows: list[dict[str, Any]] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Verdict:
    alert_id: str
    severity: Severity
    confidence: float                       # 0..1
    mitre: list[tuple[str, str]] = field(default_factory=list)  # (technique_id, name)
    narrative: str = ""
    timeline: list[tuple[str, str]] = field(default_factory=list)  # (time, event)
    recommended_action: str = ""
    actions_taken: list[str] = field(default_factory=list)
