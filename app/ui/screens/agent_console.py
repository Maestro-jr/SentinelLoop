"""Screen 2 — Live Agent Console (the hero). Streams the agent's reasoning."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
    QGraphicsOpacityEffect,
)

from app.core.models import StepEvent, StepKind
from app.ui import theme
from app.ui.widgets.gauge import PulseDot

_KIND_COLOR = {
    StepKind.THOUGHT: theme.K_THOUGHT,
    StepKind.SPL: theme.K_SPL,
    StepKind.RESULT: theme.K_RESULT,
    StepKind.DRIFT: theme.K_DRIFT,
    StepKind.HEAL: theme.K_HEAL,
    StepKind.CORRELATE: theme.K_CORRELATE,
    StepKind.CONCLUSION: theme.K_CONCLUSION,
    StepKind.ACTION: theme.K_ACTION,
    StepKind.ERROR: theme.K_ERROR,
}


class _StepCard(QFrame):
    def __init__(self, ev: StepEvent):
        super().__init__()
        self.setObjectName("step")
        color = _KIND_COLOR.get(ev.kind, theme.ACCENT)
        self.setStyleSheet(f"QFrame#step {{ border-left: 3px solid {color}; }}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(6)

        head = QHBoxLayout()
        kind = QLabel(ev.kind.value)
        kind.setObjectName("stepKind")
        kind.setStyleSheet(f"color:{color};")
        title = QLabel(ev.title)
        title.setStyleSheet("font-weight:700; font-size:13px;")
        head.addWidget(kind)
        head.addSpacing(8)
        head.addWidget(title, 1)
        lay.addLayout(head)

        if ev.body:
            body = QLabel(ev.body)
            body.setObjectName("stepBody")
            body.setWordWrap(True)
            lay.addWidget(body)

        if ev.spl:
            spl = QLabel(ev.spl)
            spl.setObjectName("spl")
            spl.setWordWrap(True)
            spl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            lay.addWidget(spl)

        if ev.rows:
            cols = list(ev.rows[0].keys())[:5]
            preview = " | ".join(cols)
            grid = QLabel("▸ " + preview + f"      ({len(ev.rows)} rows)")
            grid.setObjectName("muted")
            lay.addWidget(grid)
            for r in ev.rows[:4]:
                line = "   " + "  ·  ".join(str(r.get(c, ""))[:32] for c in cols)
                rl = QLabel(line)
                rl.setObjectName("dim")
                rl.setStyleSheet("font-family:Consolas,monospace; font-size:11px;")
                lay.addWidget(rl)


class AgentConsoleScreen(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(6)

        head_row = QHBoxLayout()
        self._head = QLabel("Live Agent Console")
        self._head.setObjectName("h1")
        head_row.addWidget(self._head)
        head_row.addSpacing(12)
        self._pulse = PulseDot()
        head_row.addWidget(self._pulse, 0, Qt.AlignmentFlag.AlignVCenter)
        self._status = QLabel("")
        self._status.setStyleSheet(f"color:{theme.ACCENT_BRIGHT}; font-weight:700;")
        head_row.addWidget(self._status, 0, Qt.AlignmentFlag.AlignVCenter)
        head_row.addStretch(1)
        root.addLayout(head_row)

        self._sub = QLabel("The agent investigates autonomously — every thought, query and finding is shown.")
        self._sub.setObjectName("dim")
        root.addWidget(self._sub)
        root.addSpacing(12)
        self._anims: list = []

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        host = QWidget()
        self._stream = QVBoxLayout(host)
        self._stream.setSpacing(10)
        self._stream.setContentsMargins(0, 0, 8, 0)
        self._stream.addStretch(1)
        self._scroll.setWidget(host)
        root.addWidget(self._scroll, 1)

    def reset(self, alert) -> None:
        while self._stream.count() > 1:
            item = self._stream.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._anims.clear()
        self._sub.setText(f"Investigating {alert.id} — {alert.title} on {alert.host}")
        self._pulse.start()
        self._status.setText("INVESTIGATING")

    def set_running(self, running: bool) -> None:
        if running:
            self._pulse.start()
            self._status.setText("INVESTIGATING")
            self._status.setStyleSheet(f"color:{theme.ACCENT_BRIGHT}; font-weight:700;")
        else:
            self._pulse.stop()
            self._status.setText("DONE")
            self._status.setStyleSheet(f"color:{theme.K_RESULT}; font-weight:700;")

    def show_error(self, msg: str) -> None:
        """Render a failed investigation instead of hanging on INVESTIGATING."""
        friendly = msg
        if "minimum free disk space" in msg or "503" in msg:
            friendly = ("Splunk refused the search — it is below its minimum free disk "
                        "space on the dispatch volume (needs ~5 GB free on C:). Free up "
                        "disk or lower [diskUsage] minFreeSpace in server.conf, then retry.")
        self.add_step(StepEvent(StepKind.ERROR, "Investigation failed", friendly))
        self._pulse.stop()
        self._status.setText("FAILED")
        self._status.setStyleSheet(f"color:{theme.K_ERROR}; font-weight:700;")

    def add_step(self, ev: StepEvent) -> None:
        card = _StepCard(ev)
        self._stream.insertWidget(self._stream.count() - 1, card)

        # fade + subtle drop-in
        effect = QGraphicsOpacityEffect(card)
        card.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", card)
        anim.setDuration(320)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        self._anims.append(anim)

        QTimer.singleShot(30, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()))
