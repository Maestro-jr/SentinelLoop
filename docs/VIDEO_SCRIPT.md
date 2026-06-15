# SentinelLoop — Demo Video Script (target: < 3:00)

> The runbook for the submission video. Rehearse twice. Run in **DEMO mode** so nothing
> touches the network. Set `SENTINEL_STEP_DELAY=0.7` (raise to ~1.0 if you narrate slowly).
>
> **As we build, log every new film-worthy moment in "Strong moments to film" below.**

---

## Setup before recording
- `SENTINEL_MODE=DEMO`, `SENTINEL_STEP_DELAY=0.7`
- Window maximized, screen-record at 1080p, hide other apps.
- Delete any old `audit_log.csv` so the "audit written" action is fresh.
- Have the Verdict screen pre-tested once so timing is known.

---

## Shot list (with the line you say)

**0:00–0:18 — Hook (talking head or voiceover over the Alert Queue)**
> "SOC analysts run the same 30-minute investigation on every alert — and the dashboards
> that automate it silently break when the data schema changes. This is SentinelLoop: an
> agent that does the investigation itself, in SPL, and heals its own queries when they
> break."

**0:18–0:35 — Alert Queue**
- Show the three notables. Hover the top one (CRITICAL PowerShell beacon).
> "Splunk hands us a notable: suspicious PowerShell and an outbound beacon on a finance
> workstation. Watch the agent take it."
- Click **Investigate →**.

**0:35–1:05 — Live Agent Console: reasoning + first SPL**
- Agent states its plan, writes SPL #1 (process tree).
> "It reasons about what it needs, then writes its own SPL — the process tree for that host."

**1:05–1:35 — ⭐ THE MONEY MOMENT: schema drift + self-heal**
- The query hits `process_name` → **DRIFT** card (amber) → **HEAL** card (violet) → retry succeeds.
> "Here's the key moment. That query used a field that no longer exists — exactly what
> breaks a hand-built dashboard. The agent *detects the drift, rewrites the SPL to the
> current data model, and reruns it.* It heals itself."
- **This is the clip we lead the submission thumbnail with.**

**1:35–2:05 — Console: corroborate + correlate**
- SPL #2 (network beacon to malicious IP), SPL #3 (lateral logon). Correlate cards appear.
> "It confirms a 60-second C2 beacon to a known-malicious IP, then finds the attacker
> moved laterally to a file server. It's connecting findings, not just listing them."

**2:05–2:35 — Verdict screen**
- Show severity CRITICAL, 86% confidence, MITRE chips, narrative.
> "Verdict: critical, 86% confidence, mapped to MITRE ATT&CK, with a plain-English story
> any responder can act on."

**2:35–2:55 — Approve + actions**
- Click **Approve & Execute**. Point at the actions-taken strip.
> "One click approves. It writes an audit record to CSV *and* annotates the event back in
> Splunk — human-in-the-loop, fully logged."

**2:55–3:00 — Close**
> "SentinelLoop: an agentic, self-healing SOC analyst on Splunk. Open source. Thanks."

---

## Strong moments to film (KEEP THIS UPDATED as features land)

| Moment | Screen | Slot | Why it lands | Status |
|---|---|---|---|---|
| Schema-drift detection → self-heal | Agent Console | 1:05–1:35 | The signature wow; the failure that kills dashboards, survived live | ✅ built |
| Agent writing its own SPL step-by-step | Agent Console | 0:35–1:05 | Proves it's agentic, not a chatbot | ✅ built |
| Correlation cards ("connecting findings") | Agent Console | 1:35–2:05 | Shows reasoning, not listing | ✅ built |
| Animated confidence gauge fills to 86% | Verdict | 2:05–2:35 | Eye-catching, makes the verdict feel "computed" | ✅ built |
| Verdict: severity + MITRE chips + narrative | Verdict | 2:05–2:35 | Credible SOC output | ✅ built |
| Approve → CSV audit + Splunk write-back strip | Verdict | 2:35–2:55 | Closes the loop; adoptable | ✅ built |
| Step cards fade in + live "INVESTIGATING" pulse | Agent Console | 0:35–2:05 | Makes the console feel alive/real-time | ✅ built |
| Alert Queue dashboard reveal (spinning radars + live ECG + donut) | Alert Queue | 0:18–0:35 | Instant "this is a real product" credibility | ✅ built |
| Sidebar collapse/expand animation | Alert Queue | optional B-roll | Shows polish; good transition shot | ✅ built |
| **DEMO/LIVE pill = real Splunk** — show the pill on LIVE while the queue holds real BOTS v3 alerts | Alert Queue top bar | 0:18 | Proves it's hitting a real Splunk, not a mockup | ✅ built |
| **Honest live schema-drift heal on real data** — `process_name` query returns 0 rows → agent heals to `New_Process_Name` → real rows from `index=botsv3` | Agent Console | 0:50–1:15 | THE money moment, and it's genuine (no fakery) | ✅ built |
| Verdict written back to Splunk + CSV audit (actions strip) | Verdict | 2:20 | Closes the loop; adoptable by a real SOC | ✅ built |
| *(add new ones here as we build)* | | | | |

> **Live-vs-demo call:** the strongest jury moment is running the hero investigation in
> **LIVE mode against BOTS v3** so the drift-heal and SPL are demonstrably real. Keep DEMO
> mode loaded in a second window as the network-proof fallback if Splunk hiccups on stage.

> **Opening-shot tip:** linger 2–3s on the Alert Queue first — the radars sweep, the
> Agent Status ECG beats, and the green health dots pulse. That live motion in the first
> frames sells "production SOC tool" before the agent even runs.

> **Filming tip:** the confidence gauge animates on entry — cut to the Verdict screen
> *fresh* (don't pre-load it) so the gauge sweeps to 86% on camera at ~2:05.

## Backup plans if something misbehaves on camera
- Drift heal not dramatic enough → raise `SENTINEL_STEP_DELAY` to 1.0–1.2.
- Live Splunk flaky → stay in DEMO; the experience is identical and never fails.
- Verdict feels thin → narrate the MITRE chips one by one to fill the beat.
