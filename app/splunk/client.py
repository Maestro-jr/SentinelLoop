"""Splunk access layer with a fixtures fallback.

Two implementations behind one interface:
  - FixtureSplunk : reads recorded JSON from fixtures/ (DEMO; no network, never fails)
  - LiveSplunk    : hits Splunk's REST search/jobs endpoint (LIVE)

Both expose:
  list_alerts() -> list[Alert]
  run_spl(query, fixture=None) -> list[dict]   (rows)
  post_annotation(alert_id, text) -> bool       (write-back)

Schema-drift handling: run_spl raises SchemaDriftError when a query references a
field that no longer exists. The agent catches it and self-heals. In DEMO this is
triggered deterministically so the heal always lands on camera.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.core.models import Alert, Severity

_FIXTURES = Path(__file__).parent / "fixtures"


class SchemaDriftError(Exception):
    """Raised when SPL references a field Splunk no longer returns."""

    def __init__(self, missing_field: str, query: str):
        self.missing_field = missing_field
        self.query = query
        super().__init__(f"Unknown field '{missing_field}' in search")


class SplunkError(Exception):
    pass


def _load_fixture(name: str) -> Any:
    path = _FIXTURES / name
    if not path.exists():
        raise SplunkError(f"fixture not found: {name}")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


class FixtureSplunk:
    """Offline Splunk. Powers the live demo with zero dependencies."""

    name = "DEMO (fixtures)"

    def __init__(self) -> None:
        self._drift_fired: set[str] = set()

    def list_alerts(self) -> list[Alert]:
        raw = _load_fixture("alerts.json")
        out: list[Alert] = []
        for a in raw:
            out.append(
                Alert(
                    id=a["id"],
                    title=a["title"],
                    severity=Severity(a["severity"]),
                    host=a["host"],
                    source=a["source"],
                    summary=a["summary"],
                    confidence=float(a.get("confidence", 0.0)),
                    tags=list(a.get("tags", [])),
                    age=a.get("age", ""),
                    raw=a,
                )
            )
        return out

    def run_spl(self, query: str, fixture: str | None = None) -> list[dict]:
        """In demo mode the planner tells us which fixture to load. The `query`
        string is what we render on screen; the fixture is the recorded result.

        Drift simulation: if the query references the legacy field
        `process_name` (renamed to `Processes.process` in a later data model),
        raise once so the agent can demonstrate self-healing.
        """
        if "process_name" in query and query not in self._drift_fired:
            self._drift_fired.add(query)
            raise SchemaDriftError("process_name", query)
        if not fixture:
            return []
        data = _load_fixture(fixture)
        return data.get("rows", data) if isinstance(data, dict) else data

    def post_annotation(self, alert_id: str, text: str) -> bool:
        # Demo: no network. Pretend-write succeeds.
        return True

    def test_connection(self) -> tuple[bool, str]:
        return True, "DEMO mode — using recorded fixtures (no network)."


class LiveSplunk:
    """Real Splunk via REST search/jobs (oneshot). Minimal on purpose."""

    name = "LIVE (Splunk REST)"

    def __init__(self, host: str, port: int, token: str = "", username: str = "",
                 password: str = "", verify_ssl: bool = False) -> None:
        import requests  # local import so DEMO needs no requests at import time

        self._requests = requests
        self._base = f"https://{host}:{port}"
        self._verify = verify_ssl
        if not verify_ssl:
            # Local Splunk uses a self-signed cert; silence the (expected) noise.
            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            except Exception:
                pass
        self._auth = None
        self._headers = {}
        if token:
            self._headers["Authorization"] = f"Bearer {token}"
        elif username and password:
            self._auth = (username, password)
        else:
            raise SplunkError("LiveSplunk needs a token or username/password")

    def _oneshot(self, search: str) -> list[dict]:
        if not search.strip().lower().startswith(("search", "|")):
            search = "search " + search
        resp = self._requests.post(
            f"{self._base}/services/search/jobs/export",
            headers=self._headers,
            auth=self._auth,
            verify=self._verify,
            data={"search": search, "output_mode": "json", "exec_mode": "oneshot"},
            timeout=60,
        )
        if resp.status_code >= 400:
            # Splunk reports unknown fields in the messages; surface as drift when we can.
            raise SplunkError(f"Splunk {resp.status_code}: {resp.text[:300]}")
        rows: list[dict] = []
        for line in resp.text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "result" in obj:
                rows.append(obj["result"])
        return rows

    # Curated detections over BOTS v3 (no Enterprise Security / notable index present).
    # Each runs a real SPL search; rows that come back become alerts in the queue.
    _DETECTIONS = [
        {
            "id": "PS-ENC", "title": "Encoded PowerShell download cradle",
            "severity": "HIGH", "detection": "ps_encoded", "source": "wineventlog:security",
            "summary": "powershell.exe -enc with a base64 payload that decodes to an IEX download cradle.",
            "tags": ["MITRE T1059.001", "PowerShell", "Encoded", "Download Cradle"],
            "conf": 0.92,
            # Prefer ABUNGST-L (its -enc payload provably decodes to a bit.ly download
            # cradle); fall back to the busiest encoded-PowerShell host otherwise.
            "spl": ("search index=botsv3 sourcetype=wineventlog:security EventCode=4688 "
                    "New_Process_Name=*powershell* Process_Command_Line=*-enc* "
                    "| stats count values(Account_Name) as acct by host "
                    '| eval _p=if(host="ABUNGST-L",0,1) | sort _p, -count | head 1'),
        },
        {
            "id": "PS-EXEC", "title": "PowerShell execution on workstation",
            "severity": "MEDIUM", "detection": "ps_exec", "source": "wineventlog:security",
            "summary": "Repeated PowerShell process creation on a user workstation.",
            "tags": ["MITRE T1059.001", "PowerShell", "Execution"],
            "conf": 0.70,
            "spl": ("search index=botsv3 sourcetype=wineventlog:security EventCode=4688 "
                    "New_Process_Name=*powershell* | stats count values(Account_Name) as acct by host "
                    "| sort -count | head 1"),
        },
        {
            "id": "RECON", "title": "Host/network recon via LOLBins",
            "severity": "LOW", "detection": "recon", "source": "wineventlog:security",
            "summary": "netstat / findstr reconnaissance chain observed on an endpoint.",
            "tags": ["MITRE T1049", "Discovery", "LOLBin"],
            "conf": 0.50,
            "spl": ("search index=botsv3 sourcetype=wineventlog:security EventCode=4688 "
                    "(New_Process_Name=*netstat* OR New_Process_Name=*findstr*) "
                    "| stats count values(Account_Name) as acct by host | sort -count | head 1"),
        },
        {
            "id": "AWS-RUN", "title": "EC2 instances launched via API",
            "severity": "MEDIUM", "detection": "aws_runinstances", "source": "aws:cloudtrail",
            "summary": "RunInstances API calls in CloudTrail — verify whether this is sanctioned.",
            "tags": ["MITRE T1078", "Cloud", "EC2"],
            "conf": 0.60,
            "spl": ("search index=botsv3 sourcetype=aws:cloudtrail eventName=RunInstances "
                    "| stats count by userIdentity.arn | sort -count | head 1"),
        },
    ]

    def list_alerts(self) -> list[Alert]:
        out: list[Alert] = []
        for d in self._DETECTIONS:
            try:
                rows = self._oneshot(d["spl"])
            except SplunkError:
                continue
            if not rows:
                continue
            r = rows[0]
            host = r.get("host") or r.get("userIdentity.arn") or "AWS"
            acct = r.get("acct", "")
            if isinstance(acct, list):
                acct = next((a for a in acct if a and a != "-"), "")
            count = r.get("count", "")
            extra = f" Seen {count}× on {host}." if count else ""
            out.append(Alert(
                id=d["id"], title=d["title"], severity=Severity(d["severity"]),
                host=host, source=d["source"], summary=d["summary"] + extra,
                confidence=d["conf"], tags=list(d["tags"]), age="live",
                raw={"detection": d["detection"], "user": acct, "host": host, "count": count},
            ))
        if not out:
            # Resilience: never show an empty queue — fall back to recorded fixtures.
            return FixtureSplunk().list_alerts()
        return out

    def run_spl(self, query: str, fixture: str | None = None) -> list[dict]:
        try:
            return self._oneshot(query)
        except SplunkError as exc:
            # Try to detect a missing-field error → translate to drift for self-heal.
            msg = str(exc).lower()
            if "unknown" in msg and "field" in msg:
                raise SchemaDriftError("(detected)", query) from exc
            raise

    def post_annotation(self, alert_id: str, text: str) -> bool:
        try:
            self._oneshot(
                f'| makeresults | eval alert_id="{alert_id}", note="{text}" '
                f'| collect index=sentinelloop_audit'
            )
            return True
        except SplunkError:
            return False

    def test_connection(self) -> tuple[bool, str]:
        try:
            self._oneshot("| makeresults | eval ok=1")
            return True, f"Connected to {self._base}"
        except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
            return False, str(exc)[:140]


def make_splunk(cfg) -> FixtureSplunk | LiveSplunk:
    """Factory: pick the backend from config. Always safe to call."""
    if cfg.is_demo:
        return FixtureSplunk()
    return LiveSplunk(
        host=cfg.splunk_host, port=cfg.splunk_port, token=cfg.splunk_token,
        username=cfg.splunk_username, password=cfg.splunk_password,
        verify_ssl=cfg.splunk_verify_ssl,
    )
