"""Screen 4 — Settings. Functional controls that actually change app behaviour."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QSlider,
    QCheckBox, QScrollArea, QApplication,
)

from app import __version__
from app.ui import theme


class SettingsScreen(QWidget):
    """Reads/writes the shared `state` dict so changes take effect on the next run."""

    def __init__(self, cfg, splunk, state: dict):
        super().__init__()
        self._cfg = cfg
        self._splunk = splunk
        self._state = state

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(6)

        head = QLabel("Settings")
        head.setObjectName("h1")
        sub = QLabel("Connection, agent behaviour and audit — changes apply to the next investigation.")
        sub.setObjectName("dim")
        root.addWidget(head)
        root.addWidget(sub)
        root.addSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        host = QWidget()
        body = QVBoxLayout(host)
        body.setSpacing(16)
        body.setContentsMargins(0, 0, 8, 0)
        body.addWidget(self._connection_card())
        body.addWidget(self._agent_card())
        body.addWidget(self._about_card())
        body.addStretch(1)
        scroll.setWidget(host)
        root.addWidget(scroll, 1)

    # ── helpers ──
    def _card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        f = QFrame(); f.setObjectName("card")
        v = QVBoxLayout(f)
        v.setContentsMargins(20, 18, 20, 18)
        v.setSpacing(12)
        h = QLabel(title); h.setObjectName("h2")
        v.addWidget(h)
        return f, v

    def _row(self, key: str, value_widget: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        k = QLabel(key); k.setObjectName("setKey"); k.setFixedWidth(180)
        row.addWidget(k)
        row.addWidget(value_widget, 1)
        return row

    def _val(self, text: str, color: str = theme.TEXT) -> QLabel:
        l = QLabel(text); l.setObjectName("setVal")
        if color != theme.TEXT:
            l.setStyleSheet(f"color:{color}; font-weight:600;")
        return l

    # ── Connection ──
    def _connection_card(self) -> QFrame:
        f, v = self._card("CONNECTION")
        is_demo = self._cfg.is_demo
        mode_txt = "DEMO (fixtures)" if is_demo else "LIVE (Splunk REST)"
        v.addLayout(self._row("Mode", self._val(mode_txt, theme.K_DRIFT if is_demo else theme.K_RESULT)))
        v.addLayout(self._row("Backend", self._val(self._splunk.name)))
        v.addLayout(self._row("Splunk host", self._val(self._cfg.splunk_host or "— (none; demo)")))
        v.addLayout(self._row("Splunk port", self._val(str(self._cfg.splunk_port))))

        test_row = QHBoxLayout()
        k = QLabel("Connectivity"); k.setObjectName("setKey"); k.setFixedWidth(180)
        test_row.addWidget(k)
        self._test_btn = QPushButton("Test Connection")
        self._test_btn.setObjectName("ghost")
        self._test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._test_btn.clicked.connect(self._on_test)
        test_row.addWidget(self._test_btn, 0)
        self._test_status = QLabel("Not tested")
        self._test_status.setObjectName("muted")
        test_row.addWidget(self._test_status, 1)
        v.addLayout(test_row)
        return f

    def _on_test(self) -> None:
        self._test_status.setText("Testing…")
        self._test_status.setStyleSheet(f"color:{theme.TEXT_DIM};")
        QApplication.processEvents()
        ok, msg = self._splunk.test_connection()
        color = theme.K_RESULT if ok else theme.K_ERROR
        mark = "✓ " if ok else "✕ "
        self._test_status.setStyleSheet(f"color:{color}; font-weight:600;")
        self._test_status.setText(mark + msg)

    # ── Agent behaviour ──
    def _agent_card(self) -> QFrame:
        f, v = self._card("AGENT BEHAVIOUR")

        # step delay slider
        sr = QHBoxLayout()
        k = QLabel("Step pacing"); k.setObjectName("setKey"); k.setFixedWidth(180)
        sr.addWidget(k)
        self._delay = QSlider(Qt.Orientation.Horizontal)
        self._delay.setRange(0, 20)
        self._delay.setValue(int(self._state["step_delay"] * 10))
        self._delay.setFixedWidth(220)
        self._delay_lbl = self._val(f"{self._state['step_delay']:.1f}s between steps")
        self._delay.valueChanged.connect(self._on_delay)
        sr.addWidget(self._delay)
        sr.addSpacing(12)
        sr.addWidget(self._delay_lbl, 1)
        v.addLayout(sr)

        # write-back toggle
        self._cb_writeback = QCheckBox("Write the verdict back to Splunk (annotation)")
        self._cb_writeback.setChecked(self._state["write_back"])
        self._cb_writeback.toggled.connect(lambda b: self._state.__setitem__("write_back", b))
        v.addWidget(self._cb_writeback)

        # csv audit toggle
        self._cb_csv = QCheckBox("Append an audit record to audit_log.csv")
        self._cb_csv.setChecked(self._state["audit_csv"])
        self._cb_csv.toggled.connect(lambda b: self._state.__setitem__("audit_csv", b))
        v.addWidget(self._cb_csv)

        note = QLabel("The agent never auto-remediates — every action is gated by your Approve on the Verdict screen.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        v.addWidget(note)
        return f

    def _on_delay(self, raw: int) -> None:
        val = raw / 10.0
        self._state["step_delay"] = val
        self._delay_lbl.setText(f"{val:.1f}s between steps")

    # ── About ──
    def _about_card(self) -> QFrame:
        f, v = self._card("ABOUT")
        v.addLayout(self._row("Version", self._val(f"SentinelLoop {__version__}")))
        v.addLayout(self._row("Track", self._val("Security · Splunk Agentic Ops Hackathon")))
        v.addLayout(self._row("Planner model", self._val(self._cfg.model)))
        v.addLayout(self._row("LLM planner", self._val("enabled" if self._cfg.has_llm else "scripted / BOTS v3")))
        sec = QLabel("Secrets are read from environment / .env only — never hardcoded, logged, or committed.")
        sec.setObjectName("muted"); sec.setWordWrap(True)
        v.addWidget(sec)
        return f
