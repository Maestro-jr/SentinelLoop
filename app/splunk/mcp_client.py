"""Splunk access routed through the **Splunk MCP Server** (Model Context Protocol).

This is the "agentic" tool layer: instead of calling Splunk's REST API directly,
the agent's searches go through the official Splunk MCP server
(https://github.com/splunk/splunk-mcp-server2), which exposes Splunk as MCP tools
(`search_oneshot`, `validate_spl`, `get_indexes`, …).

`McpSplunk` subclasses `LiveSplunk` and only overrides `_oneshot()` to call the MCP
`search_oneshot` tool — so it transparently reuses all the BOTS v3 detections,
`run_spl`, `post_annotation`, and `list_alerts` logic. If the MCP server is
unreachable or the `mcp` SDK isn't installed, it falls back to direct REST so the
app never breaks.

Run the server first (see docs/MCP_SETUP.md), then set SPLUNK_MCP_URL in .env.
"""
from __future__ import annotations

import asyncio
import json
import threading
from typing import Any

from app.splunk.client import LiveSplunk, SplunkError


class McpSplunk(LiveSplunk):
    name = "LIVE (Splunk MCP Server)"

    def __init__(self, mcp_url: str, *, host: str, port: int, token: str = "",
                 username: str = "", password: str = "", verify_ssl: bool = False) -> None:
        # LiveSplunk gives us the REST fallback path + all detection/alert logic.
        super().__init__(host=host, port=port, token=token, username=username,
                         password=password, verify_ssl=verify_ssl)
        self._mcp_url = mcp_url.rstrip("/")
        self._search_tool = "search_oneshot"
        self._search_arg = "query"
        self._connected = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._session = None
        self._ctxs: list = []
        self._start_loop()
        self._connect()

    # ── background event loop (MCP SDK is async) ─────────────────────────
    def _start_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        t = threading.Thread(target=self._loop.run_forever, daemon=True, name="mcp-loop")
        t.start()

    def _run(self, coro, timeout: float = 30.0):
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result(timeout=timeout)

    def _connect(self) -> None:
        try:
            self._run(self._aconnect(), timeout=20.0)
            self._connected = True
        except Exception as exc:  # noqa: BLE001 - degrade to REST, never crash
            self._connected = False
            self._connect_error = str(exc)[:160]

    async def _aconnect(self) -> None:
        from mcp import ClientSession
        from mcp.client.sse import sse_client

        sse = sse_client(f"{self._mcp_url}/sse")
        read, write = await sse.__aenter__()
        self._ctxs.append(sse)
        session_ctx = ClientSession(read, write)
        session = await session_ctx.__aenter__()
        self._ctxs.append(session_ctx)
        await session.initialize()
        self._session = session
        # Discover the oneshot search tool + its query argument name.
        tools = await session.list_tools()
        for tool in tools.tools:
            if tool.name in ("search_oneshot", "search_export", "run_oneshot_search"):
                self._search_tool = tool.name
                props = (getattr(tool, "inputSchema", {}) or {}).get("properties", {})
                for cand in ("query", "search", "spl", "search_query"):
                    if cand in props:
                        self._search_arg = cand
                        break
                if tool.name == "search_oneshot":
                    break

    # ── the one method we override: route searches through MCP ───────────
    def _oneshot(self, search: str) -> list[dict]:
        if not self._connected or self._session is None:
            return super()._oneshot(search)
        try:
            return self._run(self._asearch(search))
        except Exception:  # noqa: BLE001 - MCP hiccup -> direct REST
            return super()._oneshot(search)

    async def _asearch(self, search: str) -> list[dict]:
        # The Splunk MCP server prepends its own "search " to any query not starting
        # with "|", so strip our leading "search " to avoid "search search ...".
        q = search.strip()
        if q[:7].lower() == "search ":
            q = q[7:].lstrip()
        # BOTS v3 is 2018 data, so search all-time (earliest=0); risk_tolerance=100
        # skips the server's SPL guardrail (lab/demo). search_oneshot returns rows
        # under the "events" key.
        args = {
            self._search_arg: q,
            "earliest_time": "0",
            "latest_time": "now",
            "output_format": "json",
            "risk_tolerance": 100,
        }
        result = await self._session.call_tool(self._search_tool, args)
        return _rows_from_mcp(result)

    def test_connection(self) -> tuple[bool, str]:
        if self._connected:
            try:
                rows = self.run_spl("| makeresults | eval ok=1")
                return True, f"Connected via Splunk MCP Server ({self._mcp_url})"
            except Exception as exc:  # noqa: BLE001
                return False, f"MCP reachable but search failed: {str(exc)[:100]}"
        return False, f"MCP unavailable ({getattr(self, '_connect_error', 'no connection')}); using direct REST"


def _rows_from_mcp(result: Any) -> list[dict]:
    """Normalize an MCP CallToolResult into a list of row dicts."""
    # Prefer structured content if the server provides it.
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        # FastMCP wraps a dict return under a top-level "result" key.
        inner = structured.get("result") if isinstance(structured.get("result"), dict) else structured
        for key in ("events", "results", "rows", "data"):
            if isinstance(inner.get(key), list):
                return inner[key]
    # Otherwise parse the text content blocks.
    text_parts: list[str] = []
    for block in getattr(result, "content", []) or []:
        t = getattr(block, "text", None)
        if t:
            text_parts.append(t)
    text = "\n".join(text_parts).strip()
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Fall back: NDJSON (one JSON object per line)
        rows: list[dict] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    rows.append(obj.get("result", obj))
            except json.JSONDecodeError:
                continue
        return rows
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("events", "results", "rows", "data"):
            if isinstance(data.get(key), list):
                return data[key]
        return [data]
    return []
