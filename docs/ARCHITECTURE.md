# SentinelLoop — Architecture

## Design principle
Three layers, strict boundaries:
- **UI (PyQt6)** consumes plain dataclasses (`StepEvent`, `Verdict`) via Qt signals. It
  never imports agent internals.
- **Agent Core** is framework-agnostic. It takes an `emit(StepEvent)` callback and knows
  nothing about Qt. A `QThread` worker adapts it to the UI.
- **Splunk layer** hides whether data comes from recorded fixtures (DEMO) or a live REST
  call (LIVE), behind one interface. Swapping is a config flag; nothing upstream changes.

This is what makes the demo bulletproof (fixtures) and the live story credible (same code
path, real Splunk) without forking logic.

## Diagram

```
                         ┌───────────────────────────────────────────────┐
                         │                  PyQt6 UI                      │
                         │  Shell (frameless, neon-purple)               │
                         │  ┌──────────┐ ┌──────────────┐ ┌──────────┐  │
                         │  │ Alert    │ │ Live Agent   │ │ Verdict  │  │
                         │  │ Queue    │ │ Console ⭐   │ │          │  │
                         │  └────┬─────┘ └──────▲───────┘ └────▲─────┘  │
                         └───────┼──────────────┼──────────────┼────────┘
            investigate(alert)   │   StepEvent  │    Verdict   │  (Qt signals)
                                 ▼              │              │
                         ┌───────────────────────────────────────────────┐
                         │              AgentWorker (QThread)             │
                         └───────────────────────┬───────────────────────┘
                                                 │ emit(StepEvent)
                         ┌───────────────────────▼───────────────────────┐
                         │                 Agent Core                     │
                         │  TriageAgent loop:                             │
                         │   perceive → reason → act → SELF-HEAL →        │
                         │   verify → decide → act                        │
                         │  Planner:  ScriptedPlanner | LLMPlanner(Claude)│
                         └───────────────────────┬───────────────────────┘
              run_spl / list_alerts /            │        ▲ SchemaDriftError
              post_annotation                    ▼        │ (triggers heal)
                         ┌───────────────────────────────────────────────┐
                         │                Splunk layer                    │
                         │   FixtureSplunk (fixtures/*.json)   [DEMO]     │
                         │   LiveSplunk  (REST search/jobs/export) [LIVE] │
                         └───────────────────────┬───────────────────────┘
                                                 ▼
                         ┌───────────────────────────────────────────────┐
                         │          Splunk  (data + AI Assistant)         │
                         └───────────────────────────────────────────────┘
```

## The agentic loop
1. **Perceive** — `list_alerts()` returns Splunk notables.
2. **Reason** — `Planner.plan(alert)` produces an ordered list of `InvestigationStep`
   (a thought + the SPL to run + how to correlate the result).
3. **Act** — `run_spl(query)` executes the search.
4. **Self-heal** — if `run_spl` raises `SchemaDriftError` (a field no longer exists), the
   loop emits DRIFT, asks the planner for a healed query (`healed_spl` in demo, or
   `LLMPlanner.heal_spl` via Claude in live), re-runs, emits HEAL.
5. **Verify / correlate** — each result is correlated into the running picture.
6. **Decide** — produce a `Verdict` (severity, confidence, MITRE ATT&CK, narrative, timeline).
7. **Act** — append a CSV audit row + `post_annotation()` write-back to Splunk, gated by a
   human Approve in the UI.

## Component map
| Path | Responsibility |
|---|---|
| `app/core/config.py` | Env/.env config; DEMO-safe defaults; secret handling |
| `app/core/models.py` | `Alert`, `StepEvent`/`StepKind`, `Verdict`, `Severity` dataclasses |
| `app/splunk/client.py` | `FixtureSplunk`, `LiveSplunk`, `SchemaDriftError`, `make_splunk()` |
| `app/splunk/fixtures/` | Recorded JSON: alerts + per-step search results |
| `app/agent/planner.py` | `ScriptedPlanner`, `LLMPlanner`, `InvestigationStep`, `Plan` |
| `app/agent/loop.py` | `TriageAgent` — the loop + self-heal + actions |
| `app/agent/worker.py` | `AgentWorker(QThread)` — non-blocking bridge to the UI |
| `app/ui/theme.py` | Neon-purple tokens + global QSS |
| `app/ui/shell.py` | Frameless window, sidebar, stacked screens, wiring |
| `app/ui/screens/` | `alert_queue`, `agent_console`, `verdict`, `settings` |
| `app/ui/widgets/gauge.py` | `ConfidenceGauge` (animated arc), `PulseDot` (pulsing status dot) |
| `app/ui/widgets/radar.py` | `RadarWidget` — always-sweeping radar dial, tinted per severity |
| `app/ui/widgets/monitors.py` | `EcgMonitor` — live hospital-style heartbeat trace for Agent Status |
| `app/ui/widgets/charts.py` | `DonutChart` (severity overview), `TrendSparkline` (24h trend) |
| `app/ui/icons.py` | `icon_pixmap()` — QPainter-drawn line icons (no font-glyph risk) |
| `tools/record_fixtures.py` | Records live Splunk responses into fixtures (see `docs/SPLUNK_SETUP.md`) |

UI shell = frameless top bar (wordmark + search + DEMO pill + bell/gear/avatar) and a
**collapsible** sidebar (drawn nav icons + live Agent Status card with `EcgMonitor` and a
green `PulseDot` "Online" indicator). The Alert Queue is a full SOC dashboard: filterable
radar cards + an insight rail (overview donut, trend, top techniques, system health).

## Threading model
The UI thread only renders. `AgentWorker.run()` executes the loop on a background thread;
each `StepEvent` is delivered to the UI via a queued signal, so the console animates while
the agent works. `time.sleep(step_delay)` paces the visible stream for the demo.

## Security posture
- Secrets from environment only; never hardcoded/logged/committed. DEMO needs none.
- `LiveSplunk` fails closed (timeouts, status checks); errors never dump raw stack traces
  to the UI.
- Inputs crossing the Splunk boundary are constrained; write-back uses a dedicated audit
  index.
- The agent never auto-remediates — every consequential action is human-approved and
  dual-logged (CSV + Splunk).

## Swapping DEMO ↔ LIVE
`make_splunk(cfg)` returns `FixtureSplunk` unless `SENTINEL_MODE=LIVE` **and** Splunk
credentials are present. `_make_planner(cfg)` returns `LLMPlanner` only in LIVE with an
API key, else `ScriptedPlanner`. No other code branches on mode.
