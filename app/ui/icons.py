"""Vector icons drawn with QPainter — reliable on every platform (no font glyphs).

Each icon is drawn on a 24x24 grid and returned as a QPixmap, tinted to `color`.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QPixmap


def _pen(p: QPainter, color: str, w: float = 1.8) -> None:
    pen = QPen(QColor(color), w)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)


def _draw(name: str, p: QPainter, color: str) -> None:
    _pen(p, color)
    if name == "queue":            # concentric target
        p.drawEllipse(QPointF(12, 12), 9, 9)
        p.drawEllipse(QPointF(12, 12), 4.5, 4.5)
        p.setBrush(QColor(color)); p.drawEllipse(QPointF(12, 12), 1.4, 1.4)
    elif name == "console":        # terminal
        p.drawRoundedRect(QRectF(3, 4.5, 18, 15), 3, 3)
        path = QPainterPath(QPointF(7, 9)); path.lineTo(10, 12); path.lineTo(7, 15)
        p.drawPath(path)
        p.drawLine(QPointF(12, 15), QPointF(16.5, 15))
    elif name == "shield":         # verdict (shield + check)
        path = QPainterPath(QPointF(12, 3))
        path.lineTo(19, 6); path.lineTo(19, 12)
        path.cubicTo(19, 16.5, 16, 19.5, 12, 21)
        path.cubicTo(8, 19.5, 5, 16.5, 5, 12)
        path.lineTo(5, 6); path.closeSubpath()
        p.drawPath(path)
        chk = QPainterPath(QPointF(9, 12)); chk.lineTo(11, 14); chk.lineTo(15, 9.5)
        p.drawPath(chk)
    elif name == "gear":           # settings
        import math
        c = QPointF(12, 12)
        for i in range(8):
            a = math.radians(i * 45)
            p.drawLine(QPointF(12 + 7 * math.cos(a), 12 + 7 * math.sin(a)),
                       QPointF(12 + 9.5 * math.cos(a), 12 + 9.5 * math.sin(a)))
        p.drawEllipse(c, 6, 6)
        p.drawEllipse(c, 2.4, 2.4)
    elif name == "bell":
        path = QPainterPath(QPointF(7, 16.5))
        path.cubicTo(7, 9.5, 8.5, 7.5, 12, 7.5)
        path.cubicTo(15.5, 7.5, 17, 9.5, 17, 16.5)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(QPointF(5.5, 16.5), QPointF(18.5, 16.5))
        p.drawArc(QRectF(10.5, 17.5, 3, 3), 0, -180 * 16)
        p.setBrush(QColor(color)); p.drawEllipse(QPointF(12, 6), 1.2, 1.2)
    elif name == "search":
        p.drawEllipse(QPointF(10.5, 10.5), 6, 6)
        p.drawLine(QPointF(15, 15), QPointF(20, 20))
    elif name == "filter":         # sliders
        for y, kx in ((7.5, 16), (12, 9), (16.5, 14)):
            p.drawLine(QPointF(4, y), QPointF(20, y))
            p.setBrush(QColor(color)); p.drawEllipse(QPointF(kx, y), 2.1, 2.1)
            p.setBrush(Qt.BrushStyle.NoBrush)
    elif name == "plus":
        p.drawLine(QPointF(12, 6.5), QPointF(12, 17.5))
        p.drawLine(QPointF(6.5, 12), QPointF(17.5, 12))
    elif name == "menu":           # collapse / hamburger
        for y in (8, 12, 16):
            p.drawLine(QPointF(5, y), QPointF(19, y))
    elif name == "activity":       # heartbeat glyph
        path = QPainterPath(QPointF(4, 12))
        path.lineTo(8, 12); path.lineTo(10.5, 6); path.lineTo(14, 18)
        path.lineTo(16, 12); path.lineTo(20, 12)
        p.drawPath(path)
    elif name == "kebab":          # vertical 3-dot menu
        p.setBrush(QColor(color))
        for y in (7, 12, 17):
            p.drawEllipse(QPointF(12, y), 1.5, 1.5)
    elif name == "dots":           # horizontal 3-dot menu
        p.setBrush(QColor(color))
        for x in (7, 12, 17):
            p.drawEllipse(QPointF(x, 12), 1.5, 1.5)


def icon_pixmap(name: str, color: str = "#a191c9", size: int = 20) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size / 24.0, size / 24.0)
    _draw(name, p, color)
    p.end()
    return pm


def logo_pixmap(size: int = 34) -> QPixmap:
    """The SentinelLoop mark: a faceted neon-purple hexagon with a loop glyph."""
    import math
    from PyQt6.QtGui import QLinearGradient

    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size / 24.0, size / 24.0)

    cx, cy, r = 12, 12, 11
    pts = [QPointF(cx + r * math.cos(math.radians(60 * i - 90)),
                   cy + r * math.sin(math.radians(60 * i - 90))) for i in range(6)]
    hexp = QPainterPath(pts[0])
    for pt in pts[1:]:
        hexp.lineTo(pt)
    hexp.closeSubpath()

    grad = QLinearGradient(0, 0, 24, 24)
    grad.setColorAt(0.0, QColor("#c77dff"))
    grad.setColorAt(0.55, QColor("#8b30e0"))
    grad.setColorAt(1.0, QColor("#5a189a"))
    p.fillPath(hexp, grad)

    # top-left facet highlight
    facet = QPainterPath(pts[5]); facet.lineTo(pts[0]); facet.lineTo(QPointF(cx, cy)); facet.closeSubpath()
    hi = QColor("#e0aaff"); hi.setAlpha(70)
    p.fillPath(facet, hi)

    # inner "loop" glyph (two interlocked arcs) in deep shade
    pen = QPen(QColor("#1a0b2e"), 1.8)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawArc(QRectF(7.5, 8.0, 6.0, 8.0), 90 * 16, 220 * 16)
    p.drawArc(QRectF(10.5, 8.0, 6.0, 8.0), -90 * 16, 220 * 16)
    p.end()
    return pm
