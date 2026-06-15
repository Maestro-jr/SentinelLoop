"""Spinning radar widget — one per alert card, tinted by severity. Always sweeping."""
from __future__ import annotations

import math

from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QConicalGradient
from PyQt6.QtWidgets import QWidget

from app.ui import theme


class RadarWidget(QWidget):
    def __init__(self, color: str = theme.ACCENT, size: int = 86, parent=None):
        super().__init__(parent)
        self._color = color
        self._angle = 0.0
        self.setFixedSize(size, size)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)               # ~30 fps

    def set_color(self, color: str) -> None:
        self._color = color
        self.update()

    def _tick(self) -> None:
        self._angle = (self._angle + 3.2) % 360
        self.update()

    def paintEvent(self, _evt) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor(self._color)
        cx, cy = self.width() / 2, self.height() / 2
        center = QPointF(cx, cy)
        radius = min(cx, cy) - 4

        # clip to the dial
        path_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        p.setClipRect(self.rect())

        # concentric rings
        ring = QColor(c); ring.setAlpha(70)
        p.setPen(QPen(ring, 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        for f in (1.0, 0.66, 0.33):
            r = radius * f
            p.drawEllipse(center, r, r)
        # cross-hairs
        cross = QColor(c); cross.setAlpha(45)
        p.setPen(QPen(cross, 1))
        p.drawLine(QPointF(cx - radius, cy), QPointF(cx + radius, cy))
        p.drawLine(QPointF(cx, cy - radius), QPointF(cx, cy + radius))

        # sweep (conical gradient trailing wedge)
        grad = QConicalGradient(center, -self._angle)
        lead = QColor(c); lead.setAlpha(190)
        mid = QColor(c); mid.setAlpha(60)
        none = QColor(c); none.setAlpha(0)
        grad.setColorAt(0.0, lead)
        grad.setColorAt(0.12, mid)
        grad.setColorAt(0.40, none)
        grad.setColorAt(1.0, none)
        p.setBrush(grad)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(path_rect)

        # leading edge line
        edge = QColor(c); edge.setAlpha(220)
        p.setPen(QPen(edge, 1.6))
        a = math.radians(self._angle)
        p.drawLine(center, QPointF(cx + radius * math.cos(a), cy - radius * math.sin(a)))

        # blips + center dot
        p.setPen(Qt.PenStyle.NoPen)
        blip = QColor(c); blip.setAlpha(200)
        p.setBrush(blip)
        for bx, by, br in ((0.45, 0.35, 2.2), (-0.3, 0.5, 1.8), (0.2, -0.55, 1.6)):
            p.drawEllipse(QPointF(cx + bx * radius, cy + by * radius), br, br)
        glow = QColor(c); glow.setAlpha(255)
        p.setBrush(glow)
        p.drawEllipse(center, 3.0, 3.0)
        p.end()
