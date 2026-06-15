"""Screen 4 — Settings. Shows the active mode and connection state (read-only MVP)."""
from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QFormLayout

from app.ui import theme


class SettingsScreen(QWidget):
    def __init__(self, cfg, splunk_name: str, planner_name: str):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(12)

        head = QLabel("Settings")
        head.setObjectName("h1")
        root.addWidget(head)

        card = QFrame()
        card.setObjectName("card")
        form = QFormLayout(card)
        form.setContentsMargins(22, 20, 22, 20)
        form.setSpacing(12)

        def val(text, color=theme.TEXT):
            l = QLabel(text)
            l.setStyleSheet(f"color:{color}; font-weight:600;")
            return l

        mode = "DEMO (fixtures)" if cfg.is_demo else "LIVE (Splunk)"
        mode_color = theme.K_DRIFT if cfg.is_demo else theme.K_RESULT
        form.addRow(self._k("Mode"), val(mode, mode_color))
        form.addRow(self._k("Splunk backend"), val(splunk_name))
        form.addRow(self._k("Splunk host"), val(cfg.splunk_host or "— (none; demo)"))
        form.addRow(self._k("Planner"), val(planner_name))
        form.addRow(self._k("Model"), val(cfg.model))
        form.addRow(self._k("Step delay"), val(f"{cfg.step_delay:.1f}s"))
        root.addWidget(card)

        note = QLabel(
            "Secrets are read from environment / .env only — never hardcoded or logged.\n"
            "Set SENTINEL_MODE=LIVE plus SPLUNK_HOST + token to talk to a real Splunk.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        root.addWidget(note)
        root.addStretch(1)

    def _k(self, text):
        l = QLabel(text)
        l.setObjectName("dim")
        return l
