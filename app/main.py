"""SentinelLoop entry point."""
from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from app.core.config import load_config
from app.splunk.client import make_splunk
from app.agent.planner import ScriptedPlanner, LLMPlanner
from app.agent.botsv3_planner import BotsV3Planner
from app.ui import theme
from app.ui.shell import Shell


def _make_planner(cfg):
    if cfg.is_demo:
        return ScriptedPlanner()          # polished fixture-backed demo
    if cfg.has_llm:
        return LLMPlanner(cfg.anthropic_api_key, cfg.model)
    return BotsV3Planner()                # real SPL against index=botsv3


def main() -> int:
    cfg = load_config()
    splunk = make_splunk(cfg)
    planner = _make_planner(cfg)

    app = QApplication(sys.argv)
    app.setApplicationName("SentinelLoop")
    app.setStyleSheet(theme.QSS)

    shell = Shell(cfg, splunk, planner)
    shell.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
