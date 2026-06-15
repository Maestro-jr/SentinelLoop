"""Live ECG-style monitor (hospital-machine vibe) for the Agent Status card."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QLinearGradient
from PyQt6.QtWidgets import QWidget

from app.ui import theme


def _beat_template(length: int = 70) -> list[float]:
    """One heartbeat: flat baseline with a P-wave, QRS spike, and T-wave."""
    t = [0.0] * length
    # P wave
    t[10] = 0.12; t[11] = 0.18; t[12] = 0.12
    # QRS complex
    t[20] = -0.10
    t[21] = 0.95     # R spike
    t[22] = -0.30
    t[23] = -0.08
    # T wave
    t[34] = 0.22; t[35] = 0.30; t[36] = 0.22; t[37] = 0.10
    return t


class EcgMonitor(QWidget):
    def __init__(self, color: str = theme.K_RESULT, width: int = 150, height: int = 38, parent=None):
        super().__init__(parent)
        self._color = color
        self._template = _beat_template()
        self._n = 120
        self._buf = [0.0] * self._n
        self._phase = 0
        self.setFixedSize(width, height)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(45)

    def _tick(self) -> None:
        val = self._template[self._phase % len(self._template)]
        self._phase += 1
        self._buf.append(val)
        self._buf.pop(0)
        self.update()

    def paintEvent(self, _evt) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        mid = h * 0.6

        # faint baseline grid
        grid = QColor(self._color); grid.setAlpha(28)
        p.setPen(QPen(grid, 1))
        p.drawLine(QPointF(0, mid), QPointF(w, mid))

        pen = QPen(QColor(self._color), 1.7)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        step = w / (self._n - 1)
        amp = h * 0.42
        last = None
        for i, v in enumerate(self._buf):
            pt = QPointF(i * step, mid - v * amp)
            if last is not None:
                p.drawLine(last, pt)
            last = pt
        # bright leading dot
        if last is not None:
            p.setBrush(QColor(self._color))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(last, 2.4, 2.4)
        p.end()
