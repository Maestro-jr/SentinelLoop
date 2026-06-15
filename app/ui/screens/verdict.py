"""Screen 3 — Verdict / Incident Report. Severity, confidence, MITRE, actions."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QScrollArea,
)

from app.core.models import Verdict
from app.ui import theme
from app.ui.widgets.gauge import ConfidenceGauge


class VerdictScreen(QWidget):
    approved = pyqtSignal(object)
    rejected = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self._verdict = None
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(12)

        head = QLabel("Incident Verdict")
        head.setObjectName("h1")
        root.addWidget(head)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        host = QWidget()
        self._body = QVBoxLayout(host)
        self._body.setSpacing(14)
        self._body.addStretch(1)
        scroll.setWidget(host)
        root.addWidget(scroll, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        rej = QPushButton("Reject")
        rej.setObjectName("reject")
        rej.clicked.connect(lambda: self.rejected.emit(self._verdict))
        app = QPushButton("Approve & Execute  ✓")
        app.setObjectName("approve")
        app.clicked.connect(lambda: self.approved.emit(self._verdict))
        actions.addWidget(rej)
        actions.addWidget(app)
        root.addLayout(actions)

    def _card(self, title: str, build) -> QFrame:
        f = QFrame()
        f.setObjectName("card")
        v = QVBoxLayout(f)
        v.setContentsMargins(18, 16, 18, 16)
        v.setSpacing(8)
        h = QLabel(title)
        h.setObjectName("h2")
        v.addWidget(h)
        build(v)
        return f

    def show_verdict(self, verdict: Verdict, alert) -> None:
        self._verdict = verdict
        while self._body.count() > 1:
            item = self._body.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Header strip: severity + animated confidence gauge
        def _hdr(v):
            row = QHBoxLayout()
            row.setSpacing(20)

            gauge = ConfidenceGauge(size=132)
            gauge.set_value(verdict.confidence, verdict.severity.color, "CONFIDENCE")
            row.addWidget(gauge, 0, Qt.AlignmentFlag.AlignVCenter)

            col = QVBoxLayout()
            col.setSpacing(8)
            sev = QLabel(verdict.severity.value)
            sev.setStyleSheet(
                f"background:{verdict.severity.color}22; color:{verdict.severity.color};"
                f"border:1px solid {verdict.severity.color}; border-radius:8px; padding:8px 16px;"
                "font-weight:800; font-size:15px; letter-spacing:1px;")
            sev.setMaximumWidth(170)
            sev.setAlignment(Qt.AlignmentFlag.AlignCenter)
            who = QLabel(f"{alert.id}  ·  host {alert.host}")
            who.setObjectName("muted")
            col.addWidget(sev)
            col.addWidget(who)
            col.addStretch(1)
            row.addLayout(col)
            row.addStretch(1)
            v.addLayout(row)
        self._insert(self._card("Assessment", _hdr))

        # Narrative
        def _narr(v):
            n = QLabel(verdict.narrative)
            n.setObjectName("dim")
            n.setWordWrap(True)
            v.addWidget(n)
        self._insert(self._card("What happened", _narr))

        # MITRE
        if verdict.mitre:
            def _mitre(v):
                wrap = QHBoxLayout()
                wrap.setSpacing(8)
                for tid, name in verdict.mitre:
                    chip = QLabel(f"{tid}  {name}")
                    chip.setStyleSheet(
                        f"background:{theme.BG_HOVER}; color:{theme.TEXT};"
                        f"border:1px solid {theme.BORDER}; border-radius:8px; padding:6px 10px; font-size:11px;")
                    v.addWidget(chip)
            self._insert(self._card("MITRE ATT&CK", _mitre))

        # Recommended + actions taken
        def _act(v):
            rec = QLabel("➤  " + verdict.recommended_action)
            rec.setObjectName("dim")
            rec.setWordWrap(True)
            v.addWidget(rec)
            if verdict.actions_taken:
                strip = QLabel("   ".join("✓ " + a for a in verdict.actions_taken))
                strip.setStyleSheet(f"color:{theme.K_RESULT}; font-size:12px; font-weight:600;")
                strip.setWordWrap(True)
                v.addWidget(strip)
        self._insert(self._card("Recommended action", _act))

    def _insert(self, w):
        self._body.insertWidget(self._body.count() - 1, w)
