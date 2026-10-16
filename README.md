# Local Video MCP

A local stdio MCP server for your MacBook that turns a topic into a finished 1080 × 1920 explainer reel: topic
discovery (GitHub + RSS), research with claim-to-source mapping, script and creative direction, a validated storyboard,
semantic motion graphics in Remotion, narration, captions, music, automated QA with bounded repair, and an MP4.

**Local-first and cost-controlled.** The default `local` mode uses Ollama (or a deterministic template writer), Kokoro
(or espeak-ng), Remotion and FFmpeg — no API keys, no paid calls. Two opt-in modes add paid providers behind a budget
gate and explicit approval:

| Mode | Direction | Visuals | Paid |
|---|---|---|---|
| `local` (default) | Ollama → template; local heuristic director | Remotion | nothing |
| `claude` | Claude Opus 5.5 via the Anthropic API → falls back to local | Remotion | Claude tokens |
| `hybrid` | as `claude` | Remotion + selected cinematic footage (Higgsfield) | Claude + footage |

Docs: [Architecture](docs/ARCHITECTURE_V2.md) · [Claude](docs/CLAUDE_INTEGRATION.md) · [Higgsfield](docs/HIGGSFIELD_INTEGRATION.md) ·
[Motion system](docs/MOTION_DESIGN_SYSTEM.md) · [Cost controls](docs/COST_CONTROLS.md) · [QA](docs/QUALITY_ASSURANCE.md) ·
[Autopilot](docs/AUTOPILOT_V2.md) · [Troubleshooting](docs/TROUBLESHOOTING.md) · [Audit](reports/HYBRID_VIDEO_V2_AUDIT.md) ·
[Implementation report](reports/HYBRID_VIDEO_V2_IMPLEMENTATION.md)

**V2.2 (default look): FIELDNOTES premium.** Every reel uses the same premium publication frame and the same animated
character, with a scored frame-0 hook and a contextual, truthful CTA (Comment LINK / PROMPT / GUIDE / CODE / TOOLS)
that comes with ready-to-send resources. Docs: [Premium design system](docs/PREMIUM_DESIGN_SYSTEM.md) ·
[Character](docs/CHARACTER_IDENTITY.md) · [Formats](docs/CONTENT_FORMATS.md) · [CTA & resources](docs/CTA_RESOURCE_WORKFLOW.md) ·
[Gap audit](reports/V22_VISUAL_GAP_AUDIT.md) · [V2.2 report](reports/V22_IMPLEMENTATION_REPORT.md). Brand package: `brand/`.
Demos: `examples/demos/v22/run_demo.py A|B|C|D` → `demos/v22/<X>/`.

## Installed on this Mac

- MCP name: `local-video`; launcher `/Users/priyanshupatel/Downloads/VIDEOS/local-video-mcp/run-server.sh` (loads an optional `.env`)
- Python: isolated `.venv`, Python 3.12
- Local LLM: the Ollama model named by `model` in `config.json` (currently `qwen2.5:14b`; `health_check` reports `model_ready`)
- Voice: Kokoro voice named by `voice` in `config.json` (currently `am_adam`), US English; espeak-ng is the fallback
- Output: 1080 × 1920, 30 fps, H.264 + AAC, mastered to −14 LUFS / ≤ −1 dBTP
- The server runs on stdio only; no port, tunnel or public service.

Try: **“Use local-video to discover topics, pick one, and make a reel. Poll until it finishes and show me the video.”**
Or: **“Use local-video preview_storyboard for this plan, then create_video.”**

## MCP tools

Original tools (names, required arguments and outputs unchanged; new arguments are optional):

| Tool | Purpose |
|---|---|
| `health_check` | Dependencies, Ollama models, narration engine, Claude/Higgsfield readiness, budget switch |
| `discover_topics` | Rank recent unused topics from GitHub and RSS |
| `create_video(plan, mode?)` | Render a supplied scene plan (no LLM) |
| `create_video_from_topic(topic_id, mode?, dry_run?, approved_budget_usd?)` | Script and render a discovered topic |
| `run_autopilot_once(dry_run?, mode?)` | Discover → … → export; never publishes |
| `job_status` | State, fine-grained phase, errors, pending approvals, output paths |
| `list_videos` | Recent jobs |

New tools:

| Tool | Purpose |
|---|---|
| `preview_storyboard` | Plan/storyboard → scene summaries, planned layouts with reasons, duration, providers (instant); topic → dry-run job |
| `estimate_video_cost` | External cost upper bound and uncertainty for a mode/storyboard or an existing job |
| `create_hybrid_video` | Create in a chosen mode with an explicit `approved_budget_usd`; optional `dry_run` |
| `approve_generation` | Approve a pending paid request or a job budget; resumes a paused job |
| `review_video` / `repair_video` | Re-run QA / targeted repair on an existing job (background) |
| `list_assets` | Cached generated media with provenance |
| `get_video_report` | Creative decisions, sources and claims, spend, provider usage, timings, QA |
| `cancel_job` / `resume_job` | Cancel; resume from checkpoints after a crash, failure or approval pause |
| `plan_footage` | Higgsfield via MCP, step 1: shot list (footage keys, 9:16 prompts, model + params) for the agent to generate with the Higgsfield MCP |
| `attach_footage` | Higgsfield via MCP, step 2: attach a Higgsfield clip URL/file to a planned shot (validated, cached, provenance kept) |
| `import_motion_clip` | Add a local motion-graphics clip (e.g. exported from Claude's motion tools) for use in a scene |

Long work always returns a job ID immediately; one heavy job runs at a time.

## Command line

```sh
.venv/bin/local-video health
.venv/bin/local-video discover
.venv/bin/local-video autopilot
.venv/bin/local-video render examples/first-reel.json
.venv/bin/local-video preview examples/first-reel.json
.venv/bin/local-video status JOB_ID      # also: report, review, repair, resume
.venv/bin/python examples/demos/demo_a_local.py      # Test A (LOCAL)
.venv/bin/python examples/demos/demo_b_claude.py     # Test B (Claude-directed storyboard; --runtime for the API path)
.venv/bin/python examples/demos/demo_c_hybrid.py     # Test C (HYBRID with the mock footage provider)
npm run studio        # Remotion Studio
npm run typecheck     # strict TypeScript check
```

## Content and visuals

* **V2.2 premium renderer** (`src/premium/`, default `production.style: "premium"`): FIELDNOTES masthead + counter +
  hairline, kinetic top headline with serif selection-box emphasis, one centred object per beat, blur/expand/focus/push
  transitions chosen by a visual director, and the recurring character staged per beat (`brand/character/identity.json`).
  `production.style: "studio"` keeps the V2 renderer below.
* **`vibe_coding` format**: curated prompt before/after tips (`video_mcp/content/vibe_library.json`) → PROMPT CTA.
* **Formats**: `roundup` (GitHub repos; names, descriptions and star counts on screen come from the API) and `story`
  (full article text), alternating per `formats`; plus manual topics and supplied storyboards.
* **Storyboard v2** (`video_mcp/schemas/storyboard.py`): creative direction, sources, claims, scenes with intent, pace,
  motion, structured visual data, cinematic specs, assets and QA status. V1 plans migrate automatically.
* **Semantic layouts**: 17 original layouts + code editor, flow diagram, timeline, bar chart, browser mockup, warning
  card, split comparison, cinematic footage, and forge-approved components. Layouts are chosen by what the line means;
  complex visuals hold for the whole line. Deterministic for a given storyboard + seed.
* **Themes**: carbon, midnight, warm-editorial, minimal-white, tech-mono, soft-gradient, product-launch,
  cinematic-dark — one per video, WCAG-checked. The older styles (`paper`, `editorial`, `kinetic`, `mascot`,
  `fieldnotes`) still render when a V1 plan sets `style`.
* **Presenter**: only where motivated (hook/outro by default), or `production.character: "off"`.
* **Retention (V2.1)**: bold hook on frame 0 (`hookBold`), scrolling READMEs and connection graphs instead of static cards, ≥ 36 px body text enforced by QA, and a recap → big call-to-action ending (`outroCTA`). See the motion system doc.

## Voice, captions and sound

Kokoro narration (configurable voice, speed, pronunciation dictionary) with Kokoro's own word timestamps; espeak-ng
fallback with phrase-exact, energy-snapped word timings (flagged as estimated). Word-highlight captions in three styles,
kept inside the safe area. Procedural SFX (whoosh, pop, impact, ticks, chime) and a procedural music bed that changes
key/tempo per video and ducks under speech; `music: false` disables it. Final master −14 LUFS with measured true-peak
correction.

## Files

`data/jobs/JOB_ID/`: `video.mp4`, `poster.jpg`, `topic.json`, `script.json`, `storyboard.json`, `plan.json`,
`props.json`, `verification.json`, `decisions.json`, `estimate.json`, `costs.json`, `provenance.json`, `checks.json`,
`status.json`, `timings.json`, `worker.log`, `qa/` (technical/visual/audio/storyboard JSON, `summary.md`,
`contact_sheet.jpg`). Narration, cues and footage for rendering live in `public/jobs/JOB_ID/`; cached footage in
`data/assets/`; the budget ledger in `data/budget/`.

## Configuration

`config.json` keeps its original flat keys (`model`, `voice`, `feeds`, `keywords`, `fps`, `music`, …) and adds optional
sections: `production`, `creative_director`, `cinematic`, `budget`, `quality_control`, `narration`, `renderer`. Defaults:
LOCAL mode, paid generation **off**, explicit approval. Secrets go in `.env` (see `.env.example`), never in config,
plans, logs or reports.

## Quality boundaries

- Topic ranking is keyword relevance + freshness, not a virality measure.
- Claims are mapped to sources by word overlap and unsupported numbers are removed; this is not full fact-checking.
  Review facts before publishing.
- QA measures technical correctness, layout rules, contrast, loudness and caption sync; narrative quality, taste and
  pronunciation need a human. Scores state their basis.
- The template writer and espeak voice are honest fallbacks, noticeably plainer than Ollama/Claude and Kokoro.
- Not implemented: frame-range partial re-render (repairs re-render the whole video, reusing narration and footage),
  vision-model review, bundled forced aligners (evaluated; optional).

## Repositories and licenses

| Component | Upstream | License / role |
|---|---|---|
| MCP SDK | https://github.com/modelcontextprotocol/python-sdk | MIT; tool protocol |
| Ollama | https://github.com/ollama/ollama | MIT; local model runtime |
| Qwen2.5 | https://huggingface.co/Qwen/Qwen2.5-14B-Instruct | Apache 2.0; script model |
| Kokoro | https://github.com/hexgrad/kokoro | Apache 2.0; local speech |
| kokoro-onnx (optional) | https://github.com/thewh1teagle/kokoro-onnx | MIT; Kokoro v1.0 via onnxruntime (`scripts/fetch_kokoro_onnx.sh`); pulls phonemizer (GPL-3.0) |
| espeak-ng | https://github.com/espeak-ng/espeak-ng | GPL-3.0; fallback speech (invoked as a separate program) |
| Remotion | https://github.com/remotion-dev/remotion | Special license; free eligibility depends on usage/team |
| FFmpeg | https://ffmpeg.org | LGPL/GPL depending on build |
| feedparser | https://github.com/kurtmckee/feedparser | BSD |
| Anthropic Python SDK (optional) | https://github.com/anthropics/anthropic-sdk-python | MIT; Claude API |
| higgsfield-client (optional) | https://pypi.org/project/higgsfield-client/ | Higgsfield SDK; footage API |

Claude API usage and Higgsfield generation are billed by those providers under their terms.

## Reinstall / test

```sh
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.lock.txt
.venv/bin/pip install -r requirements-claude.lock.txt     # optional: CLAUDE/HYBRID
.venv/bin/pip install -e . --no-deps
.venv/bin/pip install -r requirements-kokoro-onnx.txt && scripts/fetch_kokoro_onnx.sh   # optional: Kokoro without PyTorch
npm ci
brew install ffmpeg espeak-ng ollama
node_modules/.bin/remotion browser ensure
.venv/bin/python -m pytest -q                             # RUN_SLOW=1 adds a real end-to-end render
npm run typecheck
```

To remove the Codex registration: `codex mcp remove local-video`. Generated files are left intact.
