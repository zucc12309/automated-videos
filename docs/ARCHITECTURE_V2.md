# Architecture (V2)

V2 extends the original local MCP rather than replacing it. Every job — V1 plan, discovered topic, manual topic,
supplied storyboard, autopilot — runs through one pipeline in one detached worker, serialized by `data/render.lock`.

```
discover_topics / manual topic / plan / storyboard
        │
        ▼
engine.worker ── DISCOVERING ── topic.json
        │
        ▼  orchestration/pipeline.py
RESEARCHING   creative/research.py      sources + facts packet (untrusted text, neutralized)
SCRIPTING     preflight: may Claude be called? (key present, paid enabled, approval)            ┐
DIRECTING     creative/director.py      Claude (Anthropic SDK)  ─fallback→ Ollama ─fallback→ template   │ decisions.json
              schemas/storyboard.py     DirectorOutput → validated Storyboard v2                         │
              creative/research.verify  claim→source mapping, unsupported numbers removed               ┘
PLANNING      estimate.json             Claude spend so far + cinematic upper bounds
 (dry_run stops here: COMPLETED with dry_run=true, topic not consumed)
AWAITING_APPROVAL (only if on_missing_approval="pause")
GENERATING_ASSETS  cost gate → cache lookup → journal → submit → poll → validated download → cache
                   providers/higgsfield_provider.py (official SDK) | MockCinematicProvider
                   any refusal/failure → approved Remotion fallback layout
SYNTHESIZING_AUDIO tts.py  Kokoro (default) | espeak-ng (fallback)   cached per scene by text hash
ALIGNING           alignment.py  Kokoro timestamps | phrase-anchored + energy-snapped estimate
RENDERING          build_props → variety.plan_layouts (semantic router) → SFX/music → Remotion → master (-14 LUFS, ≤ -1 dBTP)
VALIDATING         quality/*: technical (ffprobe/ffmpeg), layout (metadata + tokens), frames, audio → qa/
REPAIRING          quality_report.plan_repairs → targeted overrides → re-render/re-master (≤ max_repairs)
COMPLETED | FAILED (mandatory checks still failing) | CANCELED
```

## Modules

| Path | Role |
|---|---|
| `video_mcp/settings.py` | Typed config; V1 flat keys stay authoritative; V2 sections default to LOCAL / no paid generation |
| `video_mcp/schemas/storyboard.py` | Storyboard v2 (sources, claims, scenes with intent, motion, visual data, cinematic spec, assets, QA), `from_plan` migration, `to_plan_dict`, structured-output schema |
| `video_mcp/creative/` | `director.py` (mode routing + fallbacks + local heuristic director), `research.py`, `semantic_router.py`, `prompts_v2.py`, `component_forge.py` |
| `video_mcp/providers/` | `base.py` (interfaces, error classes), `claude_provider.py`, `script_providers.py` (Ollama, template), `higgsfield_provider.py` (+ mock) |
| `video_mcp/orchestration/` | `pipeline.py`, `job_state.py`, `cost_controller.py`, `asset_manager.py`, `tools.py` (sync MCP helpers) |
| `video_mcp/quality/` | `video_validation.py`, `frame_analysis.py`, `audio_analysis.py`, `quality_report.py` |
| `video_mcp/tts.py`, `alignment.py`, `security.py` | Narration engines, word timing, untrusted-input guards |
| `src/studio/` | `motion.tsx` (motion grammar), `LayoutsV2.tsx` (8 semantic layouts), `themes.json` (8 themes, shared with Python QA), `generated/` (forge output) |

## Job directory

```
data/jobs/<id>/
  request.json status.json worker.log            (V1)
  topic.json plan.json props.json checks.json provenance.json video.mp4 poster.jpg   (V1 contracts, extended)
  script.json storyboard.json verification.json decisions.json estimate.json costs.json timings.json
  approvals.json generation_journal.json checkpoints.json claude_usage.json
  qa/ technical.json visual.json audio.json storyboard.json summary.json summary.md contact_sheet.jpg repairs.json frames/
public/jobs/<id>/  scene-N.wav scene-N.json (words, visemes, sync) scene-N-ui.wav music.wav cinematic/scene_xxx.mp4
data/assets/<k>/<key>/  cached generated media + meta.json
data/budget/ledger.json  reservations and spend (locked)
```

The brief's `assets/{cinematic,graphics,audio}` layout maps to `public/jobs/<id>/` because Remotion can only load media
from `public/`; `provenance.json → assets` lists every file with provider, hash and cache key.

## State and recovery

`status.json.state` keeps the V1 values (`queued|running|completed|failed`) plus `awaiting_approval` and `canceled`;
`phase` carries the fine-grained state machine (`job_state.PHASES`) with validated transitions and a history.
Stages checkpoint their outputs (storyboard, per-scene narration keyed by text hash, generation journal), so
`resume_job` restarts a dead or failed worker without redoing finished work or re-paying for generation.
A cinematic submit whose outcome is unknown (timeout, or a crash between submit and recording the remote id) is never
resubmitted automatically — the scene falls back and the reservation is kept.

## Concurrency

One heavy job at a time (`data/render.lock`), unchanged. Budget reservations use a separate lock
(`data/budget/ledger.lock`) so dry runs and approvals in other processes cannot overspend the daily cap
(tested with 8 concurrent processes). Renders use `renderer.concurrency` Chromium tabs (default 2).
