"""QThread bridge so the agent loop never blocks the UI thread."""
from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from app.agent.loop import TriageAgent
from app.core.models import StepEvent, Verdict


class AgentWorker(QThread):
    step = pyqtSignal(object)      # StepEvent
    finished_verdict = pyqtSignal(object)  # Verdict
    failed = pyqtSignal(str)

    def __init__(self, splunk, planner, alert, step_delay: float = 0.7, parent=None):
        super().__init__(parent)
        self._alert = alert
        self._agent = TriageAgent(splunk, planner, emit=self.step.emit, step_delay=step_delay)

    def run(self) -> None:
        try:
            verdict: Verdict = self._agent.investigate(self._alert)
            self.finished_verdict.emit(verdict)
        except Exception as exc:  # never let the thread die silently
            self.failed.emit(str(exc))
