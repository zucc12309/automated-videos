# Higgsfield integration

Higgsfield is optional. LOCAL and CLAUDE modes never import it, and every HYBRID failure falls back to a Remotion scene.

There are two ways in:

| Route | Who calls Higgsfield | Credentials | Config |
|---|---|---|---|
| **MCP (default since V2.2)** | the agent (Claude Code / Claude app / Codex) through the Higgsfield MCP connector | your Higgsfield login in the connector; no keys in this repo | `cinematic.provider: "higgsfield_mcp"` |
| API adapter | this Python worker through `higgsfield-client` | `HF_KEY` in `.env` | `cinematic.provider: "higgsfield"` |

## Higgsfield as an MCP plugin (agent-brokered footage)

The Higgsfield MCP server runs in the agent, not in this Python process. So the local video MCP never calls Higgsfield and
never spends credits. The agent brokers between the two MCP servers:

```
local video MCP  plan_footage(storyboard)          -> shots: footage_key, 9:16 prompt (brand-styled), duration,
                                                      recommended model + params, attached?
Higgsfield MCP   balance / models_get               -> confirm credits and the model's parameters
(person)         approves the shots and credit cost
Higgsfield MCP   generate the shot (or pick one from show_generations)
local video MCP  attach_footage(footage_key, video_url, generation_id, model_id, credits_used)
local video MCP  create_hybrid_video(mode="hybrid", storyboard=...)  -> real footage in those scenes
```

How `attach_footage` handles a clip:

- **Download.** https only, SSRF-checked, no redirects, size cap `cinematic.max_download_mb`. A local `file_path` also works,
  for clips downloaded from higgsfield.ai.
- **Validation.** The clip is fully decoded. Landscape clips get a warning; they will be centre-cropped to 9:16.
- **Storage.** The clip goes into the content-addressed cache under the shot's key. Provenance records the generation id, model, credits,
  and the source URL without its query string.
- **Render.** The render sees a cache hit for that scene. Shots with nothing attached fall back to their Remotion layout, and
  `decisions.json` records why.

The shot list and the render use the same request and key functions (`orchestration/footage.py`), so they always agree.
Re-plan after editing a cinematic prompt or duration, or after changing `cinematic.mcp_model`.

**Defaults** (`config.json → cinematic`):

| Setting | Value |
|---|---|
| `mcp_model` | `seedance_2_0` |
| `mcp_params` | `{"mode": "fast", "resolution": "720p", "generate_audio": false}` |
| Clip length | 4–15 s |
| Brand grading suffix | `brand/motion.json → footage_style`, added to every prompt so footage matches the publication look |

Set `generate_audio` to false because the reel has its own narration and bed. The plan's `steps` tell the agent the
approval rule: never generate before the person approves the shots and credits.

**Verified in this delivery:**

- `plan_footage`, `attach_footage` (file and URL validation), the cache-key match, and a full hybrid render. In that render, scene
  1 used attached footage (provider `higgsfield_mcp`, $0 spent by the pipeline) and scene 4 fell back to the Remotion
  pull-quote.
- The footage used in that test was a locally generated test clip, **not Higgsfield output**.

**Not done yet:** a real Higgsfield generation.

- Your connector reports a free plan with 0 credits and no generation history.
- The connector attached to this session exposes only catalog, history, balance and import tools, not generation.

Once your connector offers generation and your workspace has credits, the same flow runs unchanged. Footage generated on
higgsfield.ai works today: take its URL from `show_generations` and pass it to `attach_footage`.

## What was discovered (2026-10-16)

* **Higgsfield MCP connector** (available to the interactive Claude session): catalog and balance are readable
  (`models_list`, `models_get`, `balance`), but the connector states it *cannot generate media*. The selected workspace
  reported `credits: 0`, plan `free`. The connector is also not reachable from the local Python worker. It was used only
  to snapshot the video-model catalog into `video_mcp/data/higgsfield_catalog.json`.
* **Official Python SDK** `higgsfield-client` 0.2.0 (inspected source): `submit(application, arguments, webhook_url=None)`
  → controller with `request_id`; `status(request_id)` → Queued / InProgress / Completed / Failed / NSFW / Cancelled;
  `result(request_id)`; `cancel(request_id)`; uploads via presigned URLs. Credentials: `HF_KEY`, or `HF_API_KEY` +
  `HF_API_SECRET`. Base URL `https://api.higgsfield.ai`. Pricing per Higgsfield's help center is pay-as-you-go from a
  USD balance, video billed per second.
* Not available in the SDK: a cost-estimate endpoint, client idempotency keys, lookup by client key, and a model
  catalog endpoint. Website automation, scraping and cookie reuse are not used.

## Adapter (`providers/higgsfield_provider.py`)

`CinematicProvider` interface: `capabilities()`, `estimate_cost(request)`, `submit(request, idempotency_key)`,
`get_status(remote_id)`, `fetch_result(remote_id)`.

* `cinematic.application` — the SDK endpoint id for your chosen model. Required; never derived or guessed.
* `cinematic.model_label` — a catalog id (e.g. `seedance1_5`) used to validate aspect ratio, duration and resolution
  before submission and to send only parameters that model accepts (audio generation is turned off; narration and
  SFX come from the local mix).
* Prompts come from the storyboard's neutral `CinematicSpec` (subject, lens, controlled camera move, lighting,
  negative space for typography, no text/logos) plus negative guidance.
* Results: the first `https` video URL in the result JSON is downloaded with SSRF checks (https only, no redirects, no
  private addresses), a size cap (`max_download_mb`), content-type check, `ffprobe` and a full decode pass.

## Money

There is no provider estimate, so cost = `cinematic.usd_per_second_upper_bound × seconds` **only if you set it from
Higgsfield's published price**. If it is unset, the request is "unknown cost" and needs a per-request approval with a USD
cap (`approve_generation(job_id, max_usd, request_id)`), and that cap is what is reserved. See COST_CONTROLS.md.

## Reliability

* Generation journal (`generation_journal.json`): `submitting` is written before the SDK call, `submitted` with the
  remote id after. A worker that dies in between leaves `submitting`; on resume that scene falls back with
  "outcome unknown — reconcile manually", and nothing is resubmitted.
* A submit that raises an unknown-outcome error keeps its reservation (it may have been charged).
* Polling honours `poll_interval_seconds`, `timeout_seconds` and job cancellation. NSFW/failed/canceled → fallback.

## Caching and continuity

Successful clips are stored under `data/assets/` keyed by provider, model/application, prompt, parameters, reference
hashes, seed and provider config; identical requests reuse them at zero cost. Footage is graded toward the theme in
Remotion (saturation/contrast/brightness, theme-tinted soft-light layer, legibility gradients) and accurate text is
composited on top — the model is never asked to render text or UI. Short clips are slowed (≥ 0.5×) to span their beat.

## Hook establishing shot (V2.1)

In HYBRID mode with `cinematic.enabled`, the local director adds one atmospheric shot under the hook (dark desk,
monitor glow, empty upper half for titles, no text/logos). The bold hook typography is composited on top, graded toward
the theme; if generation is not approved or fails, the hook renders without it.

## Claude motion clips and Higgsfield

The Higgsfield connector's `import-claude-motion-from-url` imports an MP4 *into Higgsfield's media library*; it needs a
signed `*.claudeusercontent.com` URL plus a download token from Claude's motion export, and it does not generate video.
The opposite direction — using a motion clip *in* a reel — is the `import_motion_clip` MCP tool (local file → validated
→ `data/motion_library/` → `library:<id>` asset).

## Enabling real footage

```sh
.venv/bin/pip install -r requirements-claude.lock.txt higgsfield-client==0.2.0
export HF_KEY=...            # or HF_API_KEY + HF_API_SECRET (put them in .env)
```
```json
"cinematic": {"enabled": true, "provider": "higgsfield", "application": "<endpoint id from your Higgsfield API docs>",
              "model_label": "seedance1_5", "usd_per_second_upper_bound": <verified price>, "max_scenes": 2},
"budget": {"allow_paid_generation": true, "approval_policy": "explicit"}
```
Then `create_hybrid_video(mode="hybrid", ..., approved_budget_usd=0.5)`.

## Status in this delivery

Adapter implemented and tested against a fake SDK (argument translation, validation, status mapping, URL extraction) and
the pipeline tested end-to-end with the mock provider, including cache reuse, missing approval, budget exhaustion,
unknown-outcome submit, crash reconciliation and corrupt output. **No real Higgsfield generation was run**: no API
credentials, 0 credits, and the application id must come from your account.
