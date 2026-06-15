"""Frameless main window: top bar + collapsible sidebar + stacked screens.

Owns the wiring: Alert Queue -> AgentWorker -> Console -> Verdict.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QStackedWidget, QButtonGroup, QLineEdit,
)

from app.agent.worker import AgentWorker
from app.ui import theme
from app.ui.icons import icon_pixmap, logo_pixmap
from app.ui.widgets.gauge import PulseDot
from app.ui.widgets.monitors import EcgMonitor
from app.ui.screens.alert_queue import AlertQueueScreen
from app.ui.screens.agent_console import AgentConsoleScreen
from app.ui.screens.verdict import VerdictScreen
from app.ui.screens.settings import SettingsScreen

_NAV = [
    ("Alert Queue", "queue", 0),
    ("Agent Console", "console", 1),
    ("Verdict", "shield", 2),
    ("Settings", "gear", 3),
]
_SIDEBAR_W = 220
_SIDEBAR_W_COLLAPSED = 68


class Shell(QMainWindow):
    def __init__(self, cfg, splunk, planner):
        super().__init__()
        self._cfg = cfg
        self._splunk = splunk
        self._planner = planner
        self._worker: AgentWorker | None = None
        self._current_alert = None
        self._drag_pos: QPoint | None = None
        self._collapsed = False
        self._nav_buttons: list[tuple[QPushButton, str]] = []

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(1320, 820)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(1, 1, 1, 1)
        outer.setSpacing(0)

        # Fetch the alert queue once (LIVE mode runs real detection searches here).
        self._alerts_cache = self._splunk.list_alerts()

        outer.addWidget(self._build_topbar())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_sidebar())

        # Shared, mutable settings the Settings screen edits and the agent reads.
        self._state = {
            "step_delay": cfg.step_delay,
            "write_back": True,
            "audit_csv": True,
        }

        self._stack = QStackedWidget()
        alerts = self._alerts_cache
        self._alerts = AlertQueueScreen()
        self._console = AgentConsoleScreen()
        self._verdict = VerdictScreen()
        self._settings_screen = SettingsScreen(cfg, splunk, self._state)
        for w in (self._alerts, self._console, self._verdict, self._settings_screen):
            self._stack.addWidget(w)
        body.addWidget(self._stack, 1)
        outer.addLayout(body, 1)

        # Wiring
        self._alerts.investigate_requested.connect(self._start_investigation)
        self._verdict.approved.connect(self._on_approved)
        self._verdict.rejected.connect(lambda v: self._goto(0))

        self._alerts.set_alerts(alerts)
        self._goto(0)

    # ── title bar ──────────────────────────────────────────────
    def _build_topbar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("titleBar")
        bar.setFixedHeight(62)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 14, 0)
        lay.setSpacing(10)

        # logo mark + wordmark
        logo = QLabel()
        logo.setPixmap(logo_pixmap(36))
        logo.setFixedSize(40, 40)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(logo, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addSpacing(4)
        wm = QVBoxLayout()
        wm.setSpacing(0)
        brand = QLabel("SENTINELLOOP")
        brand.setObjectName("brand")
        sub = QLabel("AGENTIC SOC TRIAGE")
        sub.setObjectName("brandSub")
        wm.addWidget(brand)
        wm.addWidget(sub)
        lay.addLayout(wm)
        lay.addSpacing(20)

        # search (cosmetic)
        search = QLineEdit()
        search.setObjectName("search")
        search.setPlaceholderText("Search alerts, hosts, users, IPs…        CTRL /")
        search.addAction(QIcon(icon_pixmap("search", theme.TEXT_MUTED, 18)),
                         QLineEdit.ActionPosition.LeadingPosition)
        search.setMaximumWidth(520)
        lay.addWidget(search, 1)

        lay.addStretch(0)
        # DEMO / LIVE pill
        mode = QLabel(("●  DEMO" if self._cfg.is_demo else "●  LIVE"))
        mode.setObjectName("modePill")
        col = theme.K_DRIFT if self._cfg.is_demo else theme.K_RESULT
        mode.setStyleSheet(
            f"QLabel#modePill {{ color:{col}; border:1px solid {col}; border-radius:13px;"
            "padding:5px 16px; font-weight:800; letter-spacing:1px; font-size:12px; }}")
        lay.addWidget(mode)

        lay.addWidget(self._topbar_icon("activity", lambda: None))
        lay.addWidget(self._bell(len(self._alerts_cache)))
        lay.addWidget(self._topbar_icon("gear", lambda: self._goto(3)))
        lay.addWidget(self._avatar())

        # window controls
        lay.addSpacing(6)
        for txt, name, slot in (("—", "winBtn", self.showMinimized),
                                ("▢", "winBtn", self._toggle_max),
                                ("✕", "winClose", self.close)):
            b = QPushButton(txt)
            b.setObjectName(name)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(slot)
            lay.addWidget(b)

        bar.mouseMoveEvent = self._drag
        bar.mousePressEvent = self._press
        bar.mouseDoubleClickEvent = lambda e: self._toggle_max()
        return bar

    def _topbar_icon(self, name: str, slot) -> QPushButton:
        b = QPushButton()
        b.setObjectName("iconBtn")
        b.setIcon(QIcon(icon_pixmap(name, theme.TEXT_DIM, 20)))
        b.setIconSize(QSize(20, 20))
        b.setFixedSize(38, 38)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.clicked.connect(slot)
        return b

    def _bell(self, count: int) -> QWidget:
        wrap = QWidget()
        wrap.setFixedSize(38, 38)
        btn = self._topbar_icon("bell", lambda: self._goto(0))
        btn.setParent(wrap)
        badge = QLabel(str(count), wrap)
        badge.setObjectName("badge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(
            "QLabel#badge { background:#ff4d6d; color:white; border-radius:8px;"
            "font-size:9px; font-weight:800; min-width:16px; min-height:16px; }")
        badge.move(21, 4)
        return wrap

    def _avatar(self) -> QLabel:
        av = QLabel()
        av.setFixedSize(36, 36)
        av.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {theme.ACCENT_BRIGHT},"
            f" stop:1 {theme.ACCENT_DEEP}); border-radius:18px; border:2px solid {theme.BORDER};")
        return av

    def _toggle_max(self):
        self.showNormal() if self.isMaximized() else self.showMaximized()

    def _press(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _drag(self, e):
        if self._drag_pos is not None and e.buttons() == Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    # ── sidebar ────────────────────────────────────────────────
    def _build_sidebar(self) -> QFrame:
        self._sidebar = QFrame()
        self._sidebar.setObjectName("sidebar")
        self._sidebar.setFixedWidth(_SIDEBAR_W)
        lay = QVBoxLayout(self._sidebar)
        lay.setContentsMargins(12, 14, 12, 16)
        lay.setSpacing(6)

        # collapse toggle
        self._collapse_btn = QPushButton()
        self._collapse_btn.setObjectName("iconBtn")
        self._collapse_btn.setIcon(QIcon(icon_pixmap("menu", theme.TEXT_DIM, 20)))
        self._collapse_btn.setIconSize(QSize(20, 20))
        self._collapse_btn.setFixedSize(40, 36)
        self._collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._collapse_btn.clicked.connect(self._toggle_sidebar)
        lay.addWidget(self._collapse_btn)
        lay.addSpacing(8)

        self._navgroup = QButtonGroup(self)
        self._navgroup.setExclusive(True)
        for label, icon, idx in _NAV:
            b = QPushButton("   " + label)
            b.setObjectName("navBtn")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setIcon(QIcon(icon_pixmap(icon, theme.TEXT_DIM, 20)))
            b.setIconSize(QSize(20, 20))
            b.setToolTip(label)
            b.clicked.connect(lambda _, i=idx: self._goto(i))
            self._navgroup.addButton(b, idx)
            self._nav_buttons.append((b, label))
            lay.addWidget(b)

        lay.addStretch(1)
        lay.addWidget(self._build_agent_status())

        self._footer = QLabel("Splunk Agentic Ops\nHackathon · MVP")
        self._footer.setObjectName("muted")
        lay.addWidget(self._footer)
        return self._sidebar

    def _build_agent_status(self) -> QFrame:
        self._status_card = QFrame()
        self._status_card.setObjectName("panel")
        v = QVBoxLayout(self._status_card)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)

        title = QLabel("AGENT STATUS")
        title.setObjectName("muted")
        v.addWidget(title)

        row = QHBoxLayout()
        active = QLabel("Active")
        active.setStyleSheet(f"color:{theme.TEXT}; font-weight:700; font-size:14px;")
        row.addWidget(active)
        row.addStretch(1)
        self._ecg = EcgMonitor(color=theme.K_RESULT, width=96, height=30)
        row.addWidget(self._ecg)
        v.addLayout(row)

        copilot = QHBoxLayout()
        cl = QVBoxLayout()
        cl.setSpacing(0)
        cn = QLabel("AI Copilot")
        cn.setStyleSheet(f"color:{theme.TEXT_DIM}; font-size:12px;")
        cs = QLabel("Online")
        cs.setStyleSheet(f"color:{theme.K_RESULT}; font-weight:700; font-size:12px;")
        cl.addWidget(cn)
        cl.addWidget(cs)
        copilot.addLayout(cl)
        copilot.addStretch(1)
        # connector line → pulsing online dot
        line = QLabel(); line.setFixedSize(22, 2)
        line.setStyleSheet(f"background:{theme.BORDER}; border-radius:1px;")
        copilot.addWidget(line, 0, Qt.AlignmentFlag.AlignVCenter)
        copilot.addSpacing(6)
        self._online = PulseDot(color=theme.K_RESULT)
        self._online.start()
        copilot.addWidget(self._online, 0, Qt.AlignmentFlag.AlignVCenter)
        v.addLayout(copilot)
        return self._status_card

    def _toggle_sidebar(self):
        self._collapsed = not self._collapsed
        target = _SIDEBAR_W_COLLAPSED if self._collapsed else _SIDEBAR_W
        anim = QPropertyAnimation(self._sidebar, b"minimumWidth", self)
        anim2 = QPropertyAnimation(self._sidebar, b"maximumWidth", self)
        for a in (anim, anim2):
            a.setDuration(220)
            a.setStartValue(self._sidebar.width())
            a.setEndValue(target)
            a.setEasingCurve(QEasingCurve.Type.InOutCubic)
            a.start()
        self._anim_keep = (anim, anim2)

        for btn, label in self._nav_buttons:
            btn.setText("" if self._collapsed else "   " + label)
        self._status_card.setVisible(not self._collapsed)
        self._footer.setVisible(not self._collapsed)

    def _goto(self, idx: int):
        self._stack.setCurrentIndex(idx)
        btn = self._navgroup.button(idx)
        if btn:
            btn.setChecked(True)

    # ── investigation flow ─────────────────────────────────────
    def _start_investigation(self, alert):
        self._current_alert = alert
        self._console.reset(alert)
        self._goto(1)
        self._worker = AgentWorker(
            self._splunk, self._planner, alert,
            step_delay=self._state["step_delay"],
            write_back=self._state["write_back"],
            audit_csv=self._state["audit_csv"])
        self._worker.step.connect(self._console.add_step)
        self._worker.finished_verdict.connect(self._on_verdict)
        self._worker.failed.connect(self._console.show_error)
        self._worker.start()

    def _on_verdict(self, verdict):
        self._console.set_running(False)
        self._verdict.show_verdict(verdict, self._current_alert)
        self._goto(2)

    def _on_approved(self, verdict):
        self._goto(0)
