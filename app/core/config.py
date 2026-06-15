"""Central configuration. Reads .env; safe defaults to DEMO mode.

Security note: secrets are read from the environment only — never hardcoded,
never logged. Demo mode requires no credentials at all.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # dotenv is optional
    pass


def _bool(val: str | None, default: bool = False) -> bool:
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    mode: str                 # "DEMO" or "LIVE"
    step_delay: float
    splunk_host: str
    splunk_port: int
    splunk_token: str
    splunk_username: str
    splunk_password: str
    splunk_verify_ssl: bool
    splunk_mcp_url: str
    anthropic_api_key: str
    model: str

    @property
    def has_splunk(self) -> bool:
        return bool(self.splunk_host) and (
            bool(self.splunk_token) or (bool(self.splunk_username) and bool(self.splunk_password))
        )

    @property
    def has_llm(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def is_demo(self) -> bool:
        # Demo unless explicitly LIVE *and* we actually have a Splunk to talk to.
        return self.mode.upper() != "LIVE" or not self.has_splunk


def load_config() -> Config:
    return Config(
        mode=os.getenv("SENTINEL_MODE", "DEMO"),
        step_delay=float(os.getenv("SENTINEL_STEP_DELAY", "0.7") or 0.7),
        splunk_host=os.getenv("SPLUNK_HOST", "").strip(),
        splunk_port=int(os.getenv("SPLUNK_PORT", "8089") or 8089),
        splunk_token=os.getenv("SPLUNK_TOKEN", "").strip(),
        splunk_username=os.getenv("SPLUNK_USERNAME", "").strip(),
        splunk_password=os.getenv("SPLUNK_PASSWORD", "").strip(),
        splunk_verify_ssl=_bool(os.getenv("SPLUNK_VERIFY_SSL"), False),
        splunk_mcp_url=os.getenv("SPLUNK_MCP_URL", "").strip(),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        model=os.getenv("SENTINEL_MODEL", "claude-opus-4-8").strip(),
    )
