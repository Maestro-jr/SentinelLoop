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
  (`search/jobs/export`); alerts come from Splunk notables.
- **Splunk AI / LLM reasoning:** an LLM planner (Claude `claude-opus-4-8`, or Splunk's
  AI Assistant for SPL in a live deployment) turns the agent's intent into SPL and
  **rewrites broken SPL on schema drift**. The triage decision is an agentic loop, not a
  single prompt.

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

### Going live against real Splunk

```bash
cp .env.example .env
# set SENTINEL_MODE=LIVE, SPLUNK_HOST, SPLUNK_TOKEN (or username/password)
# optional: ANTHROPIC_API_KEY for LLM-generated SPL healing
python run.py
```

| Variable | Meaning |
|---|---|
| `SENTINEL_MODE` | `DEMO` (fixtures) or `LIVE` (real Splunk) |
| `SPLUNK_HOST` / `SPLUNK_PORT` | Splunk REST endpoint (default port 8089) |
| `SPLUNK_TOKEN` *or* `SPLUNK_USERNAME`/`SPLUNK_PASSWORD` | Auth |
| `ANTHROPIC_API_KEY` / `SENTINEL_MODEL` | Optional LLM planner |
| `SENTINEL_STEP_DELAY` | Seconds between on-screen steps (drama dial) |

Secrets are read from the environment only — never hardcoded, logged, or committed.

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

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for detail. Pitch:
[`docs/PITCH.md`](docs/PITCH.md). Demo runbook: [`docs/VIDEO_SCRIPT.md`](docs/VIDEO_SCRIPT.md).

## Repository layout

```
SentinelLoop/
├── run.py                     # launcher
├── app/
│   ├── core/                  # config.py, models.py (dataclasses)
│   ├── splunk/                # client.py (fixtures | REST) + fixtures/*.json
│   ├── agent/                 # planner.py, loop.py, worker.py
│   └── ui/                    # theme.py, shell.py, screens/
│   └── ui/widgets/            # gauge.py (ConfidenceGauge, PulseDot)
├── tools/                     # record_fixtures.py (live → fixtures recorder)
├── docs/                      # ARCHITECTURE · PITCH · VIDEO_SCRIPT · SPLUNK_SETUP
├── tests/                     # agent-loop tests
├── requirements.txt
└── .env.example
```

## Track alignment

**Security track** + the hackathon's core **agentic** theme: a visible
perceive→reason→act→verify loop over Splunk data, with LLM-driven SPL and self-healing
resilience. Built solo-friendly, demoable in under 3 minutes.

## License

MIT.
