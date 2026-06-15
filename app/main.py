"""SentinelLoop entry point."""
from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from app.core.config import load_config
from app.splunk.client import make_splunk
from app.agent.planner import ScriptedPlanner
from app.agent.botsv3_planner import BotsV3Planner
from app.ui import theme
from app.ui.shell import Shell


def _make_planner(cfg):
    if cfg.is_demo:
        return ScriptedPlanner()          # polished fixture-backed demo
    if cfg.has_llm:
        # Genuinely autonomous: an LLM decides each next SPL from the last result.
        from app.agent.llm import OpenAICompatLLM
        from app.agent.autonomous import AutonomousPlanner
        return AutonomousPlanner(
            OpenAICompatLLM(cfg.llm_base_url, cfg.llm_api_key, cfg.llm_model))
    return BotsV3Planner()                # real SPL against index=botsv3 (deterministic)


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
