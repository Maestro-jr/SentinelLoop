#!/usr/bin/env python3
"""Record live Splunk responses into fixtures so the demo can run offline.

Usage:
  # record an arbitrary search into a fixture file
  python tools/record_fixtures.py search 'index=botsv3 sourcetype=*sysmon* EventCode=1 | head 20' search_process.json

  # record the alert list used by the Alert Queue
  python tools/record_fixtures.py alerts

Requires LIVE Splunk env vars (SPLUNK_HOST + token/credentials). See docs/SPLUNK_SETUP.md.
The output drops into app/splunk/fixtures/ — commit it so DEMO mode replays real data.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import load_config
from app.splunk.client import LiveSplunk

_FIXTURES = Path(__file__).resolve().parent.parent / "app" / "splunk" / "fixtures"


def _live() -> LiveSplunk:
    cfg = load_config()
    if not cfg.splunk_host:
        sys.exit("No SPLUNK_HOST set. Configure .env for LIVE mode first (see docs/SPLUNK_SETUP.md).")
    return LiveSplunk(
        host=cfg.splunk_host, port=cfg.splunk_port, token=cfg.splunk_token,
        username=cfg.splunk_username, password=cfg.splunk_password,
        verify_ssl=cfg.splunk_verify_ssl,
    )


def record_search(spl: str, outfile: str) -> None:
    rows = _live().run_spl(spl)
    out = _FIXTURES / outfile
    out.write_text(json.dumps({"rows": rows}, indent=2), encoding="utf-8")
    print(f"wrote {len(rows)} rows -> {out}")


def record_alerts() -> None:
    alerts = _live().list_alerts()
    payload = [
        {
            "id": a.id, "title": a.title, "severity": a.severity.value,
            "host": a.host, "source": a.source, "summary": a.summary,
            "confidence": a.confidence, "tags": a.tags, "age": a.age, **a.raw,
        }
        for a in alerts
    ]
    out = _FIXTURES / "alerts.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {len(payload)} alerts -> {out}")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "alerts":
        record_alerts()
    elif cmd == "search" and len(sys.argv) == 4:
        record_search(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
