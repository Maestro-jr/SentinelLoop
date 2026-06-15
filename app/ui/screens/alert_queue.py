"""Screen 1 — Alert Queue. Rich SOC dashboard: filtered cards + insight rail."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea,
    QProgressBar, QButtonGroup, QGraphicsDropShadowEffect,
)

from app.core.models import Alert, Severity
from app.ui import theme
from app.ui.icons import icon_pixmap
from app.ui.widgets.radar import RadarWidget
from app.ui.widgets.charts import DonutChart, TrendSparkline
from app.ui.widgets.gauge import PulseDot


def _tag_chip(text: str) -> QLabel:
    chip = QLabel(text)
    accent = text.startswith("MITRE")
    chip.setStyleSheet(
        f"background:{theme.BG_HOVER if not accent else theme.ACCENT_DEEP};"
        f"color:{theme.TEXT_DIM if not accent else 'white'};"
        f"border:1px solid {theme.BORDER}; border-radius:7px; padding:3px 9px; font-size:11px;")
    return chip


def _kebab() -> QPushButton:
    b = QPushButton()
    b.setObjectName("iconBtn")
    b.setIcon(QIcon(icon_pixmap("kebab", theme.TEXT_MUTED, 18)))
    b.setIconSize(QSize(18, 18))
    b.setFixedSize(26, 26)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


class _AlertCard(QFrame):
    investigate = pyqtSignal(object)
    case_toggled = pyqtSignal(object, bool)

    def __init__(self, alert: Alert):
        super().__init__()
        self.setObjectName("card")
        self._alert = alert
        self._in_case = False
        col = alert.severity.color

        # soft neon glow
        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(30)
        glow.setOffset(0, 3)
        gc = QColor(theme.ACCENT_GLOW); gc.setAlpha(85)
        glow.setColor(gc)
        self.setGraphicsEffect(glow)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(18)

        # radar (severity-coloured, always sweeping)
        lay.addWidget(RadarWidget(color=col, size=92), 0, Qt.AlignmentFlag.AlignVCenter)

        # middle
        mid = QVBoxLayout()
        mid.setSpacing(7)
        top = QHBoxLayout()
        top.setSpacing(10)
        chip = QLabel(alert.severity.value)
        chip.setStyleSheet(
            f"background:{col}22; color:{col}; border:1px solid {col};"
            "border-radius:7px; padding:4px 12px; font-weight:800; font-size:11px; letter-spacing:1px;")
        top.addWidget(chip, 0, Qt.AlignmentFlag.AlignVCenter)
        title = QLabel(alert.title)
        title.setStyleSheet("font-size:15px; font-weight:700;")
        title.setWordWrap(True)
        top.addWidget(title, 1)
        # live indicator or age
        if alert.age == "live":
            live = PulseDot(color=theme.K_RESULT)
            live.start()
            ll = QLabel("live"); ll.setStyleSheet(f"color:{theme.K_RESULT}; font-size:11px; font-weight:700;")
            top.addWidget(ll, 0, Qt.AlignmentFlag.AlignVCenter)
            top.addWidget(live, 0, Qt.AlignmentFlag.AlignVCenter)
        else:
            age = QLabel(alert.age); age.setObjectName("muted")
            top.addWidget(age, 0, Qt.AlignmentFlag.AlignTop)
        top.addWidget(_kebab(), 0, Qt.AlignmentFlag.AlignTop)
        mid.addLayout(top)

        meta = QLabel(f"{alert.id}   ·   host {alert.host}   ·   {alert.source}")
        meta.setObjectName("muted")
        mid.addWidget(meta)

        summ = QLabel(alert.summary)
        summ.setObjectName("dim")
        summ.setWordWrap(True)
        mid.addWidget(summ)

        tags = QHBoxLayout()
        tags.setSpacing(6)
        for t in alert.tags:
            tags.addWidget(_tag_chip(t))
        tags.addStretch(1)
        mid.addLayout(tags)
        lay.addLayout(mid, 1)

        # right column
        right = QVBoxLayout()
        right.setSpacing(8)
        cl = QLabel("AI CONFIDENCE"); cl.setObjectName("muted")
        right.addWidget(cl)
        cv = QLabel(f"{int(alert.confidence * 100)}%")
        cv.setStyleSheet(f"color:{theme.TEXT}; font-weight:800; font-size:18px;")
        right.addWidget(cv)
        bar = QProgressBar()
        bar.setRange(0, 100); bar.setValue(int(alert.confidence * 100))
        bar.setTextVisible(False); bar.setFixedHeight(6)
        bar.setStyleSheet(
            f"QProgressBar {{ background:{theme.BORDER}; border:none; border-radius:3px; }}"
            f"QProgressBar::chunk {{ background:{theme.ACCENT_BRIGHT}; border-radius:3px; }}")
        right.addWidget(bar)
        right.addSpacing(2)
        il = QLabel("IMPACT"); il.setObjectName("muted")
        right.addWidget(il)
        iv = QLabel(alert.impact)
        iv.setStyleSheet(f"color:{col}; font-weight:700; font-size:14px;")
        right.addWidget(iv)
        right.addSpacing(6)

        btn = QPushButton("Investigate  →")
        btn.setObjectName("primary")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: self.investigate.emit(self._alert))
        right.addWidget(btn)
        self._case_btn = QPushButton("  Add to Case")
        self._case_btn.setObjectName("linkBtn")
        self._case_btn.setIcon(QIcon(icon_pixmap("plus", theme.TEXT_DIM, 16)))
        self._case_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._case_btn.clicked.connect(self._toggle_case)
        right.addWidget(self._case_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        right.addStretch(1)

        rw = QWidget(); rw.setLayout(right); rw.setFixedWidth(190)
        lay.addWidget(rw)

    def _toggle_case(self) -> None:
        self._in_case = not self._in_case
        if self._in_case:
            self._case_btn.setText("  ✓ In Case")
            self._case_btn.setIcon(QIcon())
            self._case_btn.setStyleSheet(f"color:{theme.K_RESULT}; font-weight:700;")
        else:
            self._case_btn.setText("  Add to Case")
            self._case_btn.setIcon(QIcon(icon_pixmap("plus", theme.TEXT_DIM, 16)))
            self._case_btn.setStyleSheet("")
        self.case_toggled.emit(self._alert, self._in_case)


class AlertQueueScreen(QWidget):
    investigate_requested = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self._all: list[Alert] = []
        self._filter = "ALL"
        self._case_ids: set[str] = set()

        root = QHBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(18)

        # ── main column ──
        main = QVBoxLayout()
        main.setSpacing(12)
        head = QHBoxLayout()
        htext = QVBoxLayout(); htext.setSpacing(2)
        h1 = QLabel("ALERT QUEUE"); h1.setObjectName("h1")
        sub = QLabel("Autonomous triage by AI agents  ·  prioritized by risk and context")
        sub.setObjectName("dim")
        htext.addWidget(h1); htext.addWidget(sub)
        head.addLayout(htext)
        head.addStretch(1)
        self._pills_box = QHBoxLayout(); self._pills_box.setSpacing(6)
        head.addLayout(self._pills_box)
        main.addLayout(head)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        host = QWidget()
        self._list = QVBoxLayout(host)
        self._list.setSpacing(14)
        self._list.setContentsMargins(2, 2, 10, 2)
        self._list.addStretch(1)
        scroll.setWidget(host)
        main.addWidget(scroll, 1)
        main.addWidget(self._insight_bar())
        root.addLayout(main, 1)

        # ── right rail ──
        root.addWidget(self._build_rail())

    # ── filter pills ──
    def _build_pills(self) -> None:
        while self._pills_box.count():
            it = self._pills_box.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        counts = {
            "ALL": len(self._all),
            "HIGH": sum(1 for a in self._all if a.severity in (Severity.HIGH, Severity.CRITICAL)),
            "MEDIUM": sum(1 for a in self._all if a.severity == Severity.MEDIUM),
            "LOW": sum(1 for a in self._all if a.severity == Severity.LOW),
        }
        grp = QButtonGroup(self)
        for key, label in (("ALL", "All"), ("HIGH", "High"), ("MEDIUM", "Medium"), ("LOW", "Low")):
            b = QPushButton(f"{label} ({counts[key]})")
            b.setObjectName("pill")
            b.setCheckable(True)
            b.setChecked(key == self._filter)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _, k=key: self._apply_filter(k))
            grp.addButton(b)
            self._pills_box.addWidget(b)

    def _apply_filter(self, key: str) -> None:
        self._filter = key
        self._render_cards()
        self._build_pills()

    # ── right rail ──
    def _build_rail(self) -> QWidget:
        rail = QWidget()
        rail.setFixedWidth(310)
        v = QVBoxLayout(rail)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(14)

        # Alert overview
        ov = QFrame(); ov.setObjectName("card")
        ovl = QVBoxLayout(ov); ovl.setContentsMargins(16, 14, 16, 14); ovl.setSpacing(10)
        ovl.addLayout(self._rail_header("ALERT OVERVIEW"))
        row = QHBoxLayout()
        self._donut = DonutChart(size=148)
        row.addWidget(self._donut)
        legend = QVBoxLayout(); legend.setSpacing(8)
        self._legend_rows = {}
        for name, color in (("High", Severity.HIGH.color), ("Medium", Severity.MEDIUM.color),
                            ("Low", Severity.LOW.color)):
            lr = QHBoxLayout(); lr.setSpacing(8)
            dot = QLabel("●"); dot.setStyleSheet(f"color:{color}; font-size:12px;")
            nm = QLabel(name); nm.setObjectName("dim")
            val = QLabel("0"); val.setStyleSheet("font-weight:800;")
            lr.addWidget(dot); lr.addWidget(nm); lr.addStretch(1); lr.addWidget(val)
            self._legend_rows[name] = val
            legend.addLayout(lr)
        legend.addStretch(1)
        row.addLayout(legend, 1)
        ovl.addLayout(row)
        v.addWidget(ov)

        # Trend
        tr = QFrame(); tr.setObjectName("card")
        trl = QVBoxLayout(tr); trl.setContentsMargins(16, 14, 16, 10); trl.setSpacing(8)
        trl.addLayout(self._rail_header("TREND (24H)"))
        spark = TrendSparkline(
            [12, 9, 14, 11, 8, 10, 16, 13, 19, 15, 22, 18, 24, 20, 28, 23, 26, 31, 27, 34, 30, 38, 33, 41],
            height=84)
        trl.addWidget(spark)
        v.addWidget(tr)

        # Top techniques
        tt = QFrame(); tt.setObjectName("card")
        ttl = QVBoxLayout(tt); ttl.setContentsMargins(16, 14, 16, 14); ttl.setSpacing(9)
        ttl.addLayout(self._rail_header("TOP ATTACK TECHNIQUES"))
        for tid, name, n, mx in (("T1059.001", "PowerShell", 6, 6),
                                 ("T1110.001", "Brute Force", 5, 6),
                                 ("T1074.001", "Data Staging", 3, 6),
                                 ("T1041", "Exfiltration", 2, 6),
                                 ("T1003", "Credential Dumping", 2, 6)):
            ttl.addLayout(self._technique_row(tid, name, n, mx))
        v.addWidget(tt)

        # System health
        sh = QFrame(); sh.setObjectName("card")
        shl = QVBoxLayout(sh); shl.setContentsMargins(16, 14, 16, 14); shl.setSpacing(10)
        shl.addLayout(self._rail_header("SYSTEM HEALTH"))
        for label, status in (("Splunk Connection", "Healthy"), ("AI Agents", "Online"),
                              ("Planner / LLM", "Ready"), ("Data Ingestion", "Live")):
            shl.addLayout(self._health_row(label, status))
        v.addWidget(sh)
        v.addStretch(1)
        return rail

    def _rail_header(self, text: str) -> QHBoxLayout:
        row = QHBoxLayout(); row.setContentsMargins(0, 0, 0, 0)
        t = QLabel(text)
        t.setStyleSheet(f"color:{theme.TEXT_DIM}; font-weight:800; font-size:11px; letter-spacing:1.5px;")
        dots = QLabel(); dots.setPixmap(icon_pixmap("dots", theme.TEXT_MUTED, 16))
        row.addWidget(t); row.addStretch(1); row.addWidget(dots)
        return row

    def _technique_row(self, tid: str, name: str, n: int, mx: int) -> QHBoxLayout:
        row = QHBoxLayout(); row.setSpacing(8)
        idl = QLabel(tid); idl.setStyleSheet(f"color:{theme.CYAN}; font-size:11px; font-weight:700;")
        idl.setFixedWidth(64)
        nm = QLabel(name); nm.setObjectName("dim")
        bar = QProgressBar(); bar.setRange(0, mx); bar.setValue(n); bar.setTextVisible(False)
        bar.setFixedHeight(5); bar.setFixedWidth(70)
        bar.setStyleSheet(
            f"QProgressBar {{ background:{theme.BORDER}; border:none; border-radius:2px; }}"
            f"QProgressBar::chunk {{ background:{theme.ACCENT}; border-radius:2px; }}")
        cnt = QLabel(str(n)); cnt.setStyleSheet("font-weight:800;"); cnt.setFixedWidth(16)
        row.addWidget(idl); row.addWidget(nm, 1); row.addWidget(bar); row.addWidget(cnt)
        return row

    def _health_row(self, label: str, status: str) -> QHBoxLayout:
        row = QHBoxLayout(); row.setSpacing(8)
        dot = PulseDot(color=theme.K_RESULT); dot.start()
        nm = QLabel(label); nm.setObjectName("dim")
        st = QLabel(status); st.setStyleSheet(f"color:{theme.K_RESULT}; font-weight:700; font-size:12px;")
        row.addWidget(dot); row.addWidget(nm, 1); row.addWidget(st)
        return row

    def _insight_bar(self) -> QFrame:
        bar = QFrame(); bar.setObjectName("panel")
        lay = QHBoxLayout(bar); lay.setContentsMargins(16, 12, 16, 12); lay.setSpacing(12)
        dot = PulseDot(color=theme.ACCENT_BRIGHT); dot.start()
        lay.addWidget(dot)
        txt = QVBoxLayout(); txt.setSpacing(0)
        t1 = QLabel("AI COPILOT INSIGHT")
        t1.setStyleSheet(f"color:{theme.ACCENT_BRIGHT}; font-weight:800; font-size:11px; letter-spacing:1px;")
        self._insight = QLabel("…")
        self._insight.setObjectName("dim")
        txt.addWidget(t1); txt.addWidget(self._insight)
        lay.addLayout(txt, 1)
        chev = QLabel(); chev.setPixmap(icon_pixmap("dots", theme.TEXT_MUTED, 16))
        lay.addWidget(chev)
        return bar

    # ── data ──
    def set_alerts(self, alerts: list[Alert]) -> None:
        self._all = alerts
        self._render_cards()
        self._build_pills()
        self._refresh_rail()

    def _render_cards(self) -> None:
        while self._list.count() > 1:
            item = self._list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for a in self._visible():
            card = _AlertCard(a)
            card.investigate.connect(self.investigate_requested.emit)
            card.case_toggled.connect(self._on_case)
            self._list.insertWidget(self._list.count() - 1, card)

    def _visible(self) -> list[Alert]:
        if self._filter == "ALL":
            return self._all
        if self._filter == "HIGH":
            return [a for a in self._all if a.severity in (Severity.HIGH, Severity.CRITICAL)]
        if self._filter == "MEDIUM":
            return [a for a in self._all if a.severity == Severity.MEDIUM]
        return [a for a in self._all if a.severity == Severity.LOW]

    def _on_case(self, alert: Alert, added: bool) -> None:
        if added:
            self._case_ids.add(alert.id)
        else:
            self._case_ids.discard(alert.id)
        self._refresh_insight()

    def _refresh_rail(self) -> None:
        high = sum(1 for a in self._all if a.severity in (Severity.HIGH, Severity.CRITICAL))
        med = sum(1 for a in self._all if a.severity == Severity.MEDIUM)
        low = sum(1 for a in self._all if a.severity == Severity.LOW)
        self._donut.set_data(
            [(high, Severity.HIGH.color), (med, Severity.MEDIUM.color), (low, Severity.LOW.color)],
            str(len(self._all)), "Total")
        self._legend_rows["High"].setText(str(high))
        self._legend_rows["Medium"].setText(str(med))
        self._legend_rows["Low"].setText(str(low))
        self._refresh_insight()

    def _refresh_insight(self) -> None:
        high = sum(1 for a in self._all if a.severity in (Severity.HIGH, Severity.CRITICAL))
        msg = (f"{high} high-priority alert(s) need attention. "
               "1 alert chain spans PowerShell → C2 → lateral movement.")
        if self._case_ids:
            msg += f"   •   {len(self._case_ids)} alert(s) added to the active case."
        self._insight.setText(msg)
