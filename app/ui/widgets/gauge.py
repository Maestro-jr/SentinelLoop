"""Custom-painted widgets: a circular confidence gauge and a pulsing status dot."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QRectF, QTimer, pyqtProperty, QPropertyAnimation
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from PyQt6.QtWidgets import QWidget

from app.ui import theme


class ConfidenceGauge(QWidget):
    """A circular arc gauge: 0..1 fraction, colored by the verdict severity."""

    def __init__(self, size: int = 132, parent=None):
        super().__init__(parent)
        self._target = 0.0
        self._value = 0.0           # animated
        self._color = theme.ACCENT_BRIGHT
        self._label = ""
        self.setFixedSize(size, size)
        self._anim = QPropertyAnimation(self, b"value", self)
        self._anim.setDuration(900)

    def set_value(self, fraction: float, color: str, label: str = "") -> None:
        self._target = max(0.0, min(1.0, fraction))
        self._color = color
        self._label = label
        self._anim.stop()
        self._anim.setStartValue(self._value)
        self._anim.setEndValue(self._target)
        self._anim.start()

    def get_value(self) -> float:
        return self._value

    def set_value_prop(self, v: float) -> None:
        self._value = v
        self.update()

    value = pyqtProperty(float, fget=get_value, fset=set_value_prop)

    def paintEvent(self, _evt) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height())
        margin = 12
        rect = QRectF(margin, margin, side - 2 * margin, side - 2 * margin)

        # track
        track = QPen(QColor(theme.BORDER), 10)
        track.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(track)
        p.drawArc(rect, 0, 360 * 16)

        # value arc (start at top, clockwise)
        arc = QPen(QColor(self._color), 10)
        arc.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(arc)
        span = int(-self._value * 360 * 16)
        p.drawArc(rect, 90 * 16, span)

        # center text
        p.setPen(QColor(theme.TEXT))
        f = QFont("Segoe UI", int(side * 0.20), QFont.Weight.Bold)
        p.setFont(f)
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{int(self._value * 100)}%")

        if self._label:
            p.setPen(QColor(theme.TEXT_MUTED))
            p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
            lr = QRectF(rect.left(), rect.center().y() + side * 0.16,
                        rect.width(), 18)
            p.drawText(lr, Qt.AlignmentFlag.AlignCenter, self._label)
        p.end()


class PulseDot(QWidget):
    """A small breathing dot to signal 'agent working'."""

    def __init__(self, color: str = theme.ACCENT_BRIGHT, parent=None):
        super().__init__(parent)
        self._color = color
        self._phase = 0.0
        self._on = False
        self.setFixedSize(16, 16)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def start(self) -> None:
        self._on = True
        self._timer.start(40)
        self.show()

    def stop(self) -> None:
        self._on = False
        self._timer.stop()
        self.update()

    def _tick(self) -> None:
        self._phase = (self._phase + 0.08) % (2 * 3.14159)
        self.update()

    def paintEvent(self, _evt) -> None:
        import math
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor(self._color)
        if self._on:
            scale = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(self._phase))
        else:
            scale = 0.6
            c = QColor(theme.TEXT_MUTED)
        r = 5 * scale
        cx, cy = self.width() / 2, self.height() / 2
        c.setAlphaF(0.9)
        p.setBrush(c)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - r, cy - r, 2 * r, 2 * r))
        p.end()
