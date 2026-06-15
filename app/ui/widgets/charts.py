"""Static-data chart widgets for the Alert Queue right rail: donut + trend sparkline."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient, QPainterPath
from PyQt6.QtWidgets import QWidget

from app.ui import theme


class DonutChart(QWidget):
    """Severity breakdown ring with a center total."""

    def __init__(self, size: int = 150, parent=None):
        super().__init__(parent)
        self._segments: list[tuple[int, str]] = []
        self._total = 0
        self._center = "0"
        self._sub = "Total"
        self.setFixedSize(size, size)

    def set_data(self, segments: list[tuple[int, str]], center: str, sub: str = "Total") -> None:
        self._segments = segments
        self._total = sum(v for v, _ in segments) or 1
        self._center = center
        self._sub = sub
        self.update()

    def paintEvent(self, _evt) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height())
        m = 12
        rect = QRectF(m, m, side - 2 * m, side - 2 * m)

        track = QPen(QColor(theme.BORDER), 12)
        track.setCapStyle(Qt.PenCapStyle.FlatCap)
        p.setPen(track)
        p.drawArc(rect, 0, 360 * 16)

        start = 90 * 16
        for value, color in self._segments:
            span = -int(360 * 16 * value / self._total)
            pen = QPen(QColor(color), 12)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            p.drawArc(rect, start, span)
            start += span

        p.setPen(QColor(theme.TEXT))
        p.setFont(QFont("Segoe UI", int(side * 0.18), QFont.Weight.Bold))
        tr = QRectF(rect.left(), rect.center().y() - side * 0.22, rect.width(), side * 0.3)
        p.drawText(tr, Qt.AlignmentFlag.AlignCenter, self._center)
        p.setPen(QColor(theme.TEXT_MUTED))
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        sr = QRectF(rect.left(), rect.center().y() + side * 0.02, rect.width(), 16)
        p.drawText(sr, Qt.AlignmentFlag.AlignCenter, self._sub.upper())
        p.end()


class TrendSparkline(QWidget):
    """Filled area sparkline for the 24h trend."""

    def __init__(self, values: list[float] | None = None, color: str = theme.ACCENT_BRIGHT,
                 height: int = 90, parent=None):
        super().__init__(parent)
        self._values = values or []
        self._color = color
        self.setMinimumHeight(height)

    def set_values(self, values: list[float]) -> None:
        self._values = values
        self.update()

    def paintEvent(self, _evt) -> None:
        if len(self._values) < 2:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        pad = 6
        lo, hi = min(self._values), max(self._values)
        rng = (hi - lo) or 1
        step = (w - 2 * pad) / (len(self._values) - 1)

        def pt(i, v):
            x = pad + i * step
            y = h - pad - (v - lo) / rng * (h - 2 * pad)
            return QPointF(x, y)

        line = QPainterPath(pt(0, self._values[0]))
        for i, v in enumerate(self._values[1:], 1):
            line.lineTo(pt(i, v))

        area = QPainterPath(line)
        area.lineTo(QPointF(pad + (len(self._values) - 1) * step, h - pad))
        area.lineTo(QPointF(pad, h - pad))
        area.closeSubpath()
        grad = QLinearGradient(0, 0, 0, h)
        c0 = QColor(self._color); c0.setAlpha(110)
        c1 = QColor(self._color); c1.setAlpha(0)
        grad.setColorAt(0, c0); grad.setColorAt(1, c1)
        p.fillPath(area, grad)

        p.setPen(QPen(QColor(self._color), 2))
        p.drawPath(line)
        p.end()
