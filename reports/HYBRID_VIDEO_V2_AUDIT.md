# Hybrid Video V2 — Repository Audit (Phase 0)

Audit date: 2026-10-16. Audited commit: `20348eb` ("Automated reel generator: local scripts, voice, and animated studio engine").

Audit environment: the repository was audited and upgraded in a Linux cloud container (`/home/user/automated-videos`), not on the
target MacBook (`/Users/priyanshupatel/Downloads/VIDEOS/local-video-mcp/`). Paths below are repository-relative.
Hardware-specific notes (Apple Silicon, 24 GB) are recorded as assumptions, not measurements.

## 0. Baseline

| Check | Result |
|---|---|
| `python -m pytest -q` (Python 3.12 venv, `mcp==1.30.0`, `pydantic==2.14.1`) | **15 passed** in 1.7 s |
| `npm ci` | OK (Remotion 4.0.357, React 19) |
| Remotion still render (`remotion still … Explainer`) | OK with `--browser-executable` pointing at the Playwright headless shell |
| Kokoro / torch | Not installable in the audit container: `huggingface.co` and `download.pytorch.org` are blocked by the egress proxy |
| Ollama | Not installed; `ollama.com` blocked by the egress proxy |
| GitHub REST API | Reachable (repo-roundup discovery works) |
| RSS feeds (simonwillison.net, …) | Blocked by the egress proxy in the container |
| `espeak-ng` | Installed via apt during the audit (used for the new local fallback voice) |
| `reports/Reel motion and design practices.md` | **Not present** in the repository (README says it lives "one folder up" on the Mac) |

## 1. Architecture and data flow (as found)

```
MCP client ──stdio──▶ video_mcp/server.py (FastMCP, 7 tools)
                         │
                         ▼
                   video_mcp/engine.py
   discover() ──▶ sources.repo_roundups (GitHub search + readme)  ┐
                  sources.stories (RSS → full article text)       ┘──▶ data/topics.json
   start_job() ──▶ data/jobs/<id>/request.json + status.json
               └─▶ subprocess: python -m video_mcp.engine worker <id>   (detached, survives client)
   worker()   ── flock(data/render.lock) — one heavy job at a time
               ├─ topic → generate_plan() (Ollama /api/chat, JSON-schema format, 3 attempts, shape_plan validation)
               └─ produce():
                    Kokoro KPipeline per scene → ffmpeg voice chain (HPF, comp, loudnorm −16)
                    audio.word_timings (Kokoro token timestamps), audio.visemes, mouth_envelope
                    variety.choose_variant (seeded look) + split_beats + plan_layouts (17 layouts)
                    audio.beat_sfx / music_bed (procedural, ducked)
                    props.json → `remotion render src/index.tsx Explainer` → ffmpeg master (−14 LUFS / −1 dBTP)
                    poster.jpg, check_video (ffprobe), provenance.json, status=completed
```

Remotion side: `src/index.tsx` registers `Explainer` (style switch: `studio`, `paper`, `editorial`, `kinetic`, `mascot`,
`fieldnotes`) and `CharacterSheet`. `src/studio/StudioVideo.tsx` flattens scenes into beats, renders one layout per beat
inside `STAGE`, adds captions, a progress bar, the character (`src/Character.tsx`) and the audio tracks.

## 2. MCP tools and contracts

| Tool | Input | Output |
|---|---|---|
| `health_check` | – | dict: ffmpeg/espeak paths, renderer installed, Ollama models, configured model/voice, `api_keys_required: false` |
| `discover_topics` | `limit: int = 10` | `{topics, errors, basis}`; caches `data/topics.json` |
| `create_video` | `plan: Plan` | `{id, state: "queued", pid, next}` |
| `create_video_from_topic` | `topic_id: str` | same |
| `run_autopilot_once` | – | same |
| `job_status` | `job_id: str` (12 hex) | contents of `status.json` (+ dead-worker detection) |
| `list_videos` | `limit: int = 10` | `{jobs: [...]}` |

`Plan` = `{title, scenes[2..10], source_urls, style, series, repos}`; `Scene` = `{heading, narration, caption, points,
visual ∈ cards|terminal|flow|meter|hook|repo|doc|outro, item, label, emphasis, stat}`. Validators: caption is forced
to equal narration, emphasis/stat must appear in narration, English-only copy, no URLs in narration.

## 3. Rendering and audio capabilities

* 17 studio layouts: heroWord, bigNumber, quote, mascotCloseup, listStack, steps, compare, repoCard, terminal, chips,
  starMeter, deviceMock, chat, nodeGraph, hookStack, docStamp, recap (+ `loop` which replays the first beat).
* 5 transitions (whip, zoom, push, mask, cut), 3 temperaments, 3 caption styles, 6 backgrounds, 8 palettes.
* Character with 9 visemes from Kokoro phonemes, gesture poses, blinks, nods.
* Audio: per-scene Kokoro narration, procedural SFX (whoosh/pop/plug/stamp/tick/chime/impact), procedural music bed
  with offline ducking, final loudness master.

## 4. Animation limitations

1. Layout choice is **random among allowed options** (`rng.choice`) constrained only by structural rules, recency and a
   per-layout cap; it does not consider what the narration means (an API explanation can land on `chat` or `quote`).
2. No code, timeline, chart, browser, request/response-flow, warning or split-screen comparison layouts; no support for
   video footage (no `OffthreadVideo`), so cinematic B-roll cannot be composited.
3. Palette changes per video are seeded but the palette set is "fun" (paper-red, lilac-ink…); there are no premium
   editorial themes (carbon, midnight, minimal white…).
4. The character appears in every frame of every studio video — unmotivated mascot presence for editorial content.
5. Motion constants are spread through components (magic numbers for delays, distances, spring configs).
6. Every beat is 1.3–3 s regardless of content complexity; complex layouts (graphs, code) get the same time as a word.

## 5. Job lifecycle and persistence

* States: `queued → running → completed | failed`; `stage` is free text. No `canceled`, no approval state.
* Persistence is JSON files with atomic temp-file replace. Dead worker detection only in `status()` via `os.kill(pid, 0)`.
* No checkpoints: a crashed job cannot resume; re-running starts over (re-narrates, re-renders).
* No idempotency for external calls (there were none). No cancellation.
* `history_ids()`/`used_repos()` scan every job's `status.json` on each call (fine at current scale).

## 6. Existing quality checks

`check_video` only verifies width/height match config, an audio stream exists and duration > 1 s. No black/frozen-frame,
silence, clipping, loudness, frame-rate or decode-integrity checks; no frame inspection; no layout/safe-area checks.

## 7. Model, configuration and documentation inconsistencies (reconciled in V2 docs)

| Topic | README says | Code / config does | Resolution |
|---|---|---|---|
| Ollama model | `qwen2.5:7b` ("Installed on this Mac", "must be available") and also `qwen2.5:14b` (Content formats) | `config.json: "model": "qwen2.5:14b"` | `config.json` is authoritative. README now names the config key, not a hardcoded tag; `health_check` reports `model_ready`. |
| Kokoro voice | `af_heart` (Installed section) and `am_adam` (Voice section) | `config.json: "voice": "am_adam"` | Config authoritative; docs updated. |
| Music | "No background music is included. The current audio track is narration only." | `music: true` + `audio.music_bed()` renders a procedural ducked bed | Music **is** implemented. Quality-boundaries section rewritten. |
| Caption timing | "word timing estimated by word length rather than forced alignment" | Studio style uses **Kokoro per-token timestamps**; only legacy styles use `useCaption` length estimation | Docs describe both; V2 records timing source per job (`alignment.source`). |
| Script source | "Scripts use RSS titles/excerpts, not full-article verification" | `sources.article_text` fetches full article paragraphs; roundups use GitHub API + README | Docs corrected; V2 adds claim→source mapping. |
| Transitions in provenance | "0.4-second style-specific transitions" | Studio uses 0-frame scene joins with 9-frame beat transitions | Provenance now records the actual value per style. |
| Launcher | `run-server.sh` hardcodes `/Users/priyanshupatel/.nvm/...` Node path and `#!/bin/zsh` | — | Kept (Mac install), documented; V2 adds optional `REMOTION_BROWSER_EXECUTABLE`. |
| `pyproject` vs lock | `mcp>=1.12,<2` | lock pins 1.30.0; container had 2.2.0 globally | Venv uses the lock. |

## 8. Integration risks

1. **Claude**: no API key exists in the audit container (`ANTHROPIC_API_KEY` unset, no `ant` profile). A Claude Code
   subscription session is *not* an unattended API credential — runtime integration must use the Anthropic SDK with an
   explicitly configured key and is tested with mocked responses here.
2. **Higgsfield**: the Higgsfield MCP connector available to this interactive session is **catalog/balance read-only**
   ("cannot generate media"); the selected workspace reports `credits: 0`, plan `free`. The local Python worker cannot use
   that connector. The documented programmatic path is the official `higgsfield-client` Python SDK (v0.2.0 inspected:
   `submit(application, arguments, webhook_url=None) → request_id`, `status`, `result`, `cancel`, credentials via
   `HF_KEY` or `HF_API_KEY`+`HF_API_SECRET`, base `https://api.higgsfield.ai`). The SDK exposes **no cost-estimate endpoint
   and no idempotency key**, so cost must come from a user-configured upper bound + explicit approval, and an
   unknown-outcome submit must never be blindly retried. Application/endpoint IDs for video models are not hardcoded.
3. **Kokoro/Ollama unavailable in some environments** → need an honest local fallback (espeak-ng voice, deterministic
   template script) that is clearly labelled lower quality.
4. Remotion license terms apply for company use (unchanged).
5. Untrusted inputs (RSS, READMEs, model output, provider responses) flow into prompts and props — prompt-injection and
   SSRF surfaces (article fetch follows redirects to any host).
6. Concurrency: a single `flock` serialises heavy work; budget accounting across concurrent jobs needs its own lock.

## 9. Implementation sequence (executed)

1. Settings v2 with backward-compatible migration of flat `config.json` keys; provider interfaces; job state machine.
2. Storyboard v2 schema (+ migration from `Plan`), Claude provider (Anthropic SDK, structured output, usage/cost),
   Ollama provider (existing logic), deterministic template provider; semantic layout router.
3. Remotion: motion grammar + primitives, 8 premium themes, new semantic layouts, cinematic clip layer, optional
   character, component forge (sandboxed generated components).
4. Cost controller (locked ledger, reservations, approvals), asset cache, Higgsfield adapter (+ mock provider).
5. espeak fallback voice, energy-based alignment refinement, technical/visual/audio QA, bounded repair loop.
6. New MCP tools, autopilot v2 with dry-run, tests, demo renders, documentation.

## 10. Backward-compatibility requirements

* All 7 MCP tools keep names, required arguments and output keys; new parameters are optional.
* `Plan`/`Scene` JSON accepted unchanged (`examples/first-reel.json` still renders); legacy styles untouched.
* `plan.json`, `props.json`, `checks.json`, `provenance.json`, `status.json` keep their existing keys (V2 only adds keys);
  `status.state` keeps `queued|running|completed|failed` (new: `awaiting_approval`, `canceled`) and a new `phase` field
  carries the fine-grained state machine.
* Flat `config.json` keys (`model`, `voice`, `fps`, `music`, …) remain authoritative; new nested sections are optional
  and default to LOCAL mode with paid generation disabled.
* Existing job directories are never deleted or rewritten except by explicit repair on that job.
