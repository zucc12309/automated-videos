# Autopilot V2

`run_autopilot_once(dry_run=false, mode=null)` — same tool, same immediate `{id, state: "queued"}` reply as V1.

```
Discover (GitHub roundups + RSS stories, alternating formats) → rank (keyword relevance + freshness, unused only)
→ research packet + sources → script (Ollama → template) / direction (Claude only if authorized)
→ storyboard + claim verification → cost estimate → [approval, if paid and required]
→ cinematic assets (HYBRID only) → narration → alignment → render → QA → repair → export
```

## Rules

* Mode defaults to `production.mode` (`local`). LOCAL autopilot spends nothing.
* Paid providers are used only when `budget.allow_paid_generation` is true **and** `approval_policy` is
  `auto_within_budget` (unattended spending explicitly allowed), within per-video and per-day caps. Under `explicit`,
  autopilot falls back to local providers (or pauses, if `on_missing_approval: "pause"`).
* Never publishes anywhere. Output stays in `data/jobs/<id>/`.
* Topic/repo deduplication: a topic or repository counts as used only when a **non-dry-run** job **completes**.
  Failed, canceled and dry-run jobs never consume topics.
* Every provider decision (used, skipped, why, fallback) is written to `decisions.json`; failed jobs keep all
  intermediate files and `worker.log` and can be continued with `resume_job`.
* Generated cinematic assets are cached; identical requests are not regenerated.
* Formats: `roundup` and `story` (from `formats` in config) are unchanged; manual topics (`create_hybrid_video` with a
  `topic`) and supplied storyboards are new entry points. New formats plug in via `sources.py` + `director.py`.

## Dry run

`run_autopilot_once(dry_run=true)` (or `create_hybrid_video(..., dry_run=true)` / `preview_storyboard(topic=…)`) does
discovery, research, script, direction, verification and the cost estimate, then stops: `storyboard.json`,
`script.json`, `verification.json`, `estimate.json`, `costs.json` and `decisions.json` are written; no narration,
render or paid media. Claude direction still runs in a dry run if it is authorized (it is how the storyboard is made);
in LOCAL mode a dry run is free.

## Scheduling

No schedule is enabled by default. Use your MCP host's scheduler or cron to call `local-video autopilot` (CLI) or the
MCP tool. The Mac must be awake; discovery needs internet.
