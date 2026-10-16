# Cost controls

The system never makes a paid call silently. LOCAL mode (the default) has no paid providers at all.

## Modes

| Mode | Script / direction | Voice | Visuals | Paid calls |
|---|---|---|---|---|
| `local` | Ollama → template writer; local heuristic director | Kokoro → espeak-ng | Remotion | none |
| `claude` | Claude (gated) → Ollama → template | Kokoro → espeak-ng | Remotion | Claude only |
| `hybrid` | as `claude` | Kokoro → espeak-ng | Remotion + selected cinematic footage | Claude + Higgsfield |

## Configuration (`config.json → budget`)

```json
"budget": {
  "allow_paid_generation": false,      // master switch; false = no paid call, whatever else is set
  "approval_policy": "explicit",       // explicit | auto_within_budget | deny
  "on_missing_approval": "fallback",   // fallback (use local/Remotion) | pause (AWAITING_APPROVAL)
  "max_usd_per_video": 1.0,
  "max_usd_per_day": 5.0,
  "max_claude_calls_per_video": 3,
  "max_higgsfield_scenes": 2,
  "max_higgsfield_duration_seconds": 8
}
```
The brief's flat keys inside `production` (`max_cost_usd_per_video`, `allow_paid_generation`, …) are accepted and
migrated. A budget is a ceiling, not permission: under `explicit`, spending also needs an approval on the job.

## Approval workflow

1. `estimate_video_cost(mode=…, storyboard=…)` or a dry run (`create_hybrid_video(dry_run=true)` → `estimate.json`).
2. Approve:
   * job budget: `create_hybrid_video(..., approved_budget_usd=0.6)` or `approve_generation(job_id, max_usd=0.6)`;
   * a specific pending request (e.g. unknown-cost footage): `approve_generation(job_id, max_usd=0.4, request_id="req_…")`.
3. `job_status` / `get_video_report` show `approvals.json` (pending, approved) and `costs.json`.
4. With `on_missing_approval: "pause"` the job waits in `awaiting_approval`; `approve_generation` resumes it.

## Enforcement (`orchestration/cost_controller.py`)

For every paid call: estimate → policy check → per-video cap → daily cap → (explicit) job approval → **atomic
reservation** under `data/budget/ledger.lock` → call → reconcile.

* Reserved and committed amounts both count toward caps, so concurrent jobs cannot overspend (tested: 16 requests
  from 8 processes against a $1.00 day cap → exactly 3 × $0.30 granted).
* Unknown cost is never zero: no estimate → explicit per-request approval with a USD cap, and the cap is reserved.
* Reconciliation: Claude uses the API's `usage` (input, output, cache read/write) at list price; failed-before-billing
  calls release; timeouts and unknown outcomes keep the reserved upper bound.
* Paid submission whose outcome is unknown is never retried automatically.

## Fallbacks

| Situation | Result |
|---|---|
| No API key / package | Claude skipped → Ollama → template |
| Paid disabled / policy deny / no approval (fallback policy) | Claude skipped; footage → Remotion fallback layout |
| Cap would be exceeded | that call skipped; footage → fallback |
| Provider unavailable / failed / NSFW / corrupt output | fallback layout; reason in `decisions.json`, scene `qa.status = "fallback"` |

## Ledger and reports

`costs.json` per job: reservations (provider, kind, estimate, actual, known/unknown), total external USD, open
reservations, caps, today's spend, Claude usage, cache hits, local stage timings, pricing source. Claude prices are
Anthropic list prices as cached 2026-10-06 (Opus 5.5 $4/$20 per MTok, cache read $0.20; Sonnet 5.5 $2/$10;
Haiku 5.5 $0.10/$0.50) — verify before relying on them for billing. Higgsfield has no price in code: you configure it.

## Tested

`tests/test_v2_providers.py`: disabled by default, explicit approval, job cap, unknown cost, per-video and daily caps,
release, multi-process reservation race, Claude gate accounting, cache reuse at zero cost, fallback on missing approval
and on exhausted budget, pause policy, unknown-outcome submit, crash reconciliation.
