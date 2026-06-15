<h1 align="center">◆ SentinelLoop</h1>
<p align="center"><b>An autonomous SOC analyst that investigates Splunk alerts by writing its own SPL — and heals its queries when your data schema drifts.</b></p>
<p align="center">
  <i>Splunk Agentic Ops Hackathon · Security Track · PyQt6 + Splunk + Claude</i>
</p>

---

## The problem

SOC analysts drown in alerts. Each notable event needs the same tedious dance: pull the
process tree, check outbound connections, look for lateral movement, map to MITRE, write
it up. It takes 20–40 minutes per alert, and it's the same dance every time. Worse, the
**dashboards and saved searches that automate it silently break** when the underlying
data model changes (a field gets renamed in the next data onboarding) — so the automation
you trusted yesterday returns empty today and no one notices.

## What SentinelLoop does

SentinelLoop is an **agentic triage analyst**. Give it a Splunk notable event and it:

1. **Perceives** — picks up the alert from Splunk.
2. **Reasons** — decides what it needs to know next.
3. **Acts** — writes and runs its own SPL against Splunk.
4. **Self-heals** 🛡️ — if a query references a field that no longer exists (*schema
   drift*), it detects the failure, rewrites the SPL to the current data model, and
   retries — the thing that breaks brittle dashboards, the agent just routes around.
5. **Verifies & decides** — correlates findings into a verdict: severity, confidence,
   MITRE ATT&CK techniques, and a plain-English narrative.
6. **Acts again** — writes an audit record to CSV **and** posts an annotation back to
   Splunk — behind a human **Approve** gate.

You watch the whole thing happen live, step by step, in the **Agent Console**.

## Why it uses Splunk + AI

- **Splunk data:** every investigative step is a real SPL search against Splunk
  (`search/jobs/export`). The alert queue is generated from curated detections over real
  data (validated against the **BOTS v3** dataset).
- **Splunk's own AI/ML:** the agent runs Splunk-native machine learning in the loop —
  `| anomalydetection` over fleet process volume to surface statistical outlier hosts — so
  the investigation is driven by *Splunk's* AI capability, not just an external model.
- **Splunk MCP Server (optional):** the agent can route all Splunk access through the
  official [Splunk MCP server](https://github.com/splunk/splunk-mcp-server2) — a genuine
  agentic tool layer (`search_oneshot`, `validate_spl`, …). See
  [`docs/MCP_SETUP.md`](docs/MCP_SETUP.md). Falls back to direct REST if absent.
- **Autonomous LLM agent:** with an LLM key set, a genuine **ReAct loop** decides each next
  SPL *from the last result* (`AutonomousPlanner`), validates every query through the MCP
  `validate_spl` tool before running it, and is guardrailed to read-only `index=botsv3`.
  Provider-agnostic via three `LLM_*` env vars — free **Groq** by default, swappable to
  Ollama / Gemini / a Splunk-hosted model with no code change. Falls back to the
  deterministic `BotsV3Planner` if no key is set or the model errors mid-run.

---

## Quickstart

```bash
git clone <repo-url> && cd SentinelLoop
python -m venv .venv && . .venv/Scripts/activate     # Windows
pip install -r requirements.txt
python run.py            # runs in DEMO mode — no Splunk, no API keys needed
```

The app opens in **DEMO mode** using recorded fixtures, so the full experience —
including the schema-drift self-heal — works offline. This is also the safest way to
run the live demo.

### Zero-setup demo — single-file Windows app

No Python needed. Grab **`SentinelLoop.exe`** from the
[Releases](https://github.com/Maestro-jr/SentinelLoop/releases) page and double-click it —
the full demo runs offline (recorded BOTS v3 fixtures, the agent loop, schema-drift
self-heal, verdict). No Splunk, no MCP server, no API keys.

Build it yourself from source:
```bash
pip install pyinstaller
pyinstaller sentinelloop.spec      # -> dist/SentinelLoop.exe (~43 MB, offline DEMO)
```

### Going live against real Splunk

```bash
cp .env.example .env       # then edit it (see the variables below)
python run.py
```

| Variable | Meaning |
|---|---|
| `SENTINEL_MODE` | `DEMO` (fixtures) or `LIVE` (real Splunk) |
| `SPLUNK_HOST` / `SPLUNK_PORT` | Splunk REST endpoint (default port 8089) |
| `SPLUNK_TOKEN` *or* `SPLUNK_USERNAME`/`SPLUNK_PASSWORD` | Auth |
| `SPLUNK_MCP_URL` | Splunk MCP server base URL (e.g. `http://127.0.0.1:8050`); blank = direct REST |
| `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` | Autonomous LLM planner (free **Groq** by default; swappable to Ollama/Gemini/Splunk-hosted). Blank = deterministic planner |
| `SENTINEL_STEP_DELAY` | Seconds between on-screen steps (pacing) |

**Dataset:** the live experience uses Splunk's free **Boss of the SOC v3 (BOTS v3)** dataset
in `index=botsv3`. Setup + the Splunk MCP server: [`docs/SPLUNK_SETUP.md`](docs/SPLUNK_SETUP.md),
[`docs/MCP_SETUP.md`](docs/MCP_SETUP.md). Secrets are read from the environment only — never
hardcoded, logged, or committed.

---

## Screens

| Screen | What it shows |
|---|---|
| **Alert Queue** | Splunk notables awaiting triage, severity-chipped. Click *Investigate*. |
| **Live Agent Console** ⭐ | The hero. The agent's every thought, SPL query, finding, drift-detection and self-heal, streamed live with fade-in cards and a pulsing "investigating" indicator. |
| **Verdict** | Animated confidence gauge + severity, MITRE ATT&CK chips, narrative, recommended action, actions-taken strip, **Approve / Reject**. |
| **Settings** | Active mode, Splunk backend, planner, model. |

---

## Architecture

Three clean layers — UI never imports agent internals; the agent never imports Qt.

```
┌──────────────────────────── PyQt6 UI ────────────────────────────┐
│  Alert Queue → Live Agent Console → Verdict → Settings            │
└───────────────▲───────────────────────────┬──────────────────────┘
        StepEvent / Verdict (signals)        │ investigate(alert)
┌───────────────┴───────────────────────────▼──────────────────────┐
│                          Agent Core                               │
│   TriageAgent loop  ·  Planner (Scripted | LLM)  ·  self-heal     │
└───────────────▲───────────────────────────┬──────────────────────┘
            rows / SchemaDriftError          │ run_spl / list_alerts / post_annotation
┌───────────────┴───────────────────────────▼──────────────────────┐
│            Splunk layer:  FixtureSplunk  |  LiveSplunk            │
│                     Splunk  (data + AI)                            │
└───────────────────────────────────────────────────────────────────┘
```

**Full architecture diagram (required reading):** [`architecture_diagram.md`](architecture_diagram.md)
— how the app talks to Splunk, how the AI agent/models are integrated, and the data flow.
Component/file detail: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
Demo runbook: [`docs/VIDEO_SCRIPT.md`](docs/VIDEO_SCRIPT.md).

## Repository layout

```
SentinelLoop/
├── run.py                     # launcher
├── architecture_diagram.md    # required architecture diagram (Splunk + AI + data flow)
├── app/
│   ├── core/                  # config.py, models.py (dataclasses)
│   ├── splunk/                # client.py (fixtures | REST), mcp_client.py (Splunk MCP) + fixtures/*.json
│   ├── agent/                 # loop.py, planner.py, botsv3_planner.py, autonomous.py, llm.py, worker.py
│   └── ui/                    # theme.py, shell.py, icons.py, screens/, widgets/
├── tools/                     # record_fixtures.py (live → fixtures recorder)
├── docs/                      # ARCHITECTURE · VIDEO_SCRIPT · SPLUNK_SETUP · MCP_SETUP
├── tests/                     # agent-loop tests
├── sentinelloop.spec          # PyInstaller build (one-file offline .exe)
├── requirements.txt
└── .env.example
```

## Track alignment

**Security track** + the hackathon's core **agentic** theme: a visible
perceive→reason→act→verify loop over Splunk data, with LLM-driven SPL and self-healing
resilience. Built solo-friendly, demoable in under 3 minutes.

## License

MIT.
