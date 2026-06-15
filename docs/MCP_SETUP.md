# Routing the agent through the Splunk MCP Server

For the **"Best Use of Splunk MCP Server"** prize (and a stronger agentic story),
SentinelLoop can run all of its Splunk access through the official Splunk MCP server
instead of calling REST directly. The agent becomes a true MCP client; the Splunk MCP
server exposes Splunk as MCP tools (`search_oneshot`, `validate_spl`, `get_indexes`, …).

This is **opt-in**: leave `SPLUNK_MCP_URL` blank and SentinelLoop uses the verified direct
REST path. If the MCP server is set but unreachable, the client automatically falls back to
REST — the demo never breaks.

## 1. Get the Splunk MCP server
```bash
git clone https://github.com/splunk/splunk-mcp-server2
cd splunk-mcp-server2/python
cp .env.example .env
```
Edit its `.env` with the SAME Splunk connection SentinelLoop uses:
```
SPLUNK_HOST=127.0.0.1
SPLUNK_PORT=8089
SPLUNK_TOKEN=<your token>
SPLUNK_VERIFY_SSL=false
```

## 2. Run it in SSE (HTTP) mode
```bash
pip install -e .
python server.py            # choose SSE transport; note the host:port it prints
```
Note the base URL it binds to (e.g. `http://127.0.0.1:8050`). SentinelLoop connects to
`<base>/sse`.

## 3. Point SentinelLoop at it
In SentinelLoop's `.env`:
```
SENTINEL_MODE=LIVE
SPLUNK_MCP_URL=http://127.0.0.1:8050
```
Install the MCP client SDK (already in requirements):
```
pip install "mcp>=1.2"
```

## 4. Run
```bash
python run.py
```
Settings → CONNECTION → **Backend** will read **"LIVE (Splunk MCP Server)"** and
**Test Connection** confirms the MCP round-trip. Every investigation SPL now flows
agent → Splunk MCP Server → Splunk.

## How it's wired
`app/splunk/mcp_client.py` (`McpSplunk`) subclasses `LiveSplunk` and overrides only
`_oneshot()` to call the MCP `search_oneshot` tool over SSE (via the `mcp` Python SDK on a
background event loop). All detections, `run_spl`, `post_annotation`, drift-heal and
`list_alerts` logic are reused unchanged. On any MCP error it falls back to direct REST.

## Troubleshooting (issues we actually hit)
- **`FastMCP.__init__() got an unexpected keyword argument 'description'`** — newer `mcp`
  SDK dropped it. In `splunk-mcp-server2/python/server.py`, remove the
  `description=os.getenv("SERVER_DESCRIPTION", …),` line from the `FastMCP(...)` call.
- **`pip install mcp` fails with "Cannot uninstall typing-extensions … no RECORD file"** —
  delete the stale dist-info, e.g.
  `Remove-Item -Recurse <venv>/Lib/site-packages/typing_extensions-*.dist-info` for the old
  version, then `pip install "mcp>=1.2"`.
- **All searches 503 with "minimum free disk space (5000MB) reached … dispatch"** — Splunk
  refuses to run *any* search when its dispatch volume is below `minFreeSpace`. Either free
  disk on the Splunk drive, or lower the threshold:
  `POST /services/configs/conf-server/diskUsage` with `minFreeSpace=2000` (takes effect
  immediately, no restart). Long term, free real disk space — 2000 MB is a thin margin.
- **Queries silently return 0 rows** — the server prepends its own `search ` to non-pipe
  queries; SentinelLoop's `McpSplunk` already strips a leading `search ` to avoid
  `search search …`. Also note BOTS v3 is 2018 data, so the client passes `earliest_time=0`.

## Restarting the server later
After a reboot, relaunch it:
```bash
cd splunk-mcp-server2/python && python server.py   # SSE on 127.0.0.1:8050
```

## Demo tip
Show **Settings → Backend = "LIVE (Splunk MCP Server)"** and hit **Test Connection** on
camera, then run the hero investigation — every SPL the agent writes is being executed
through the Splunk MCP Server. That is the literal embodiment of "Agentic Ops".
