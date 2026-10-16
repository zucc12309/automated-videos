# Hybrid Video V2 — Implementation report

Date: 2026-10-16 · Branch: `claude/hybrid-video-v2` · Built and tested in a Linux cloud container (4 vCPU, 16.9 GB RAM),
not on the target Mac. See `HYBRID_VIDEO_V2_AUDIT.md` for the baseline (15 tests passing before any change).

## 1. What was implemented

| Milestone | Delivered |
|---|---|
| 1 Architecture & compatibility | Audit; typed backward-compatible settings (`settings.py`); provider interfaces; persistent job state machine with checkpoints, cancel and resume; security guards (SSRF, redaction, credential-free subprocess env, injection neutralizing) |
| 2 Creative direction | Storyboard v2 schema + V1 migration; Claude provider on the Anthropic SDK (structured output, prompt caching, refusal fallback, usage → cost, revision loop, error classes); Ollama provider; deterministic template writer; research packet + claim verification; semantic layout router with deterministic tie-breaks, speech-driven pacing and scene holds |
| 3 Remotion motion system | Motion grammar + primitives (`motion.tsx`); 8 premium themes shared with QA (`themes.json`); 8 new layouts (code, flow, timeline, chart, browser, warning, split compare, cinematic footage); motivated presenter; camera grammar; strict TypeScript typecheck; component forge with sandboxed promotion (StatRing promoted) |
| 4 Higgsfield & cost | `CinematicProvider` + Higgsfield adapter over the official `higgsfield-client` SDK + mock provider; locked budget ledger with reservations, approvals, per-video/day caps and reconciliation; generation journal (no blind resubmits); content-addressed asset cache; validated downloads |
| 5 Audio & QA | Narration engine abstraction (Kokoro default, espeak-ng fallback), pronunciation dictionary, acronym expansion, phrase-anchored energy-snapped timings; true-peak-corrected mastering; technical / audio / layout / frame QA; contact sheet; scored report with stated basis; bounded targeted repair loop |
| 6 Orchestration & tools | V2 pipeline behind the existing worker; 10 new MCP tools; autopilot V2 with dry run; resource awareness; docs; 3 demo videos |

## 2. Files

Created — Python: `video_mcp/{settings,security,tts,alignment,resources}.py`, `video_mcp/schemas/storyboard.py`,
`video_mcp/creative/{director,research,semantic_router,prompts_v2,component_forge}.py`,
`video_mcp/providers/{base,claude_provider,script_providers,higgsfield_provider}.py`,
`video_mcp/orchestration/{pipeline,job_state,cost_controller,asset_manager,tools}.py`,
`video_mcp/quality/{video_validation,frame_analysis,audio_analysis,quality_report}.py`, `video_mcp/data/higgsfield_catalog.json`.
Remotion: `src/studio/{motion.tsx,LayoutsV2.tsx,themes.json}`, `src/studio/generated/**`, `tsconfig.json`.
Tests: `tests/{conftest,test_v2_core,test_v2_providers,test_v2_pipeline}.py`.
Docs/examples: `docs/*.md` (8), `reports/HYBRID_VIDEO_V2_{AUDIT,IMPLEMENTATION}.md`, `examples/demos/*`,
`examples/components/StatRing.tsx`, `.env.example`, `requirements-claude.lock.txt`.

Modified: `video_mcp/{engine,server,variety}.py`, `src/{shared.tsx,studio/StudioVideo.tsx,studio/tokens.ts,studio/Backdrop.tsx}`,
`config.json` (added sections only), `package.json` (typecheck script, TypeScript dev deps), `pyproject.toml`
(optional extras, package data), `run-server.sh` (loads `.env`), `.gitignore` (root-anchored `data/`), `README.md`.

## 3. Existing functionality preserved

* All 7 original MCP tools keep names, required arguments and output keys (new arguments optional). Original 15 tests
  pass unchanged (one legacy invariant — no back-to-back layouts — caught a regression during development, now fixed).
* V1 plans render (`examples/first-reel.json` end-to-end test); V1 `Plan`/`Scene` validation, `shape_plan`, number
  grounding, discovery, deduplication, legacy styles, 17 layouts, character, SFX and music unchanged in behaviour.
* Job files keep V1 keys; `status.state` keeps V1 values; one heavy job at a time.
* Default mode is LOCAL with paid generation disabled.

## 4. New MCP tools

`preview_storyboard`, `estimate_video_cost`, `create_hybrid_video`, `approve_generation`, `review_video`,
`repair_video`, `list_assets`, `get_video_report`, `cancel_job`, `resume_job` — validated inputs (Pydantic), structured
outputs, job IDs for long work, redacted responses; covered by a real stdio MCP test.

## 5. Claude integration status

Implemented; **tested only with a mocked Anthropic client**. Model identifier verified as `claude-opus-5-5` (alias
`opus-5.5`); structured outputs, effort, prompt caching, server-side refusal fallback, usage-based cost reconciliation,
revision on invalid or ungrounded output, error classification. **No live call**: the build container has no
`ANTHROPIC_API_KEY`, and the interactive Claude Code session's credentials were deliberately not reused for the
runtime path. Demo B's storyboard was authored in the interactive session and is labelled as such
(`director.interactive: true`). To run the runtime path: `ANTHROPIC_API_KEY` in `.env`,
`budget.allow_paid_generation: true`, `python examples/demos/demo_b_claude.py --runtime`.

## 6. Higgsfield integration status

Adapter implemented against the documented SDK interface (inspected `higgsfield-client` 0.2.0); **tested with a fake SDK
and a local mock provider; no real generation**. Blockers: no Higgsfield API credentials in this environment, the
connected workspace has 0 credits on a free plan, the MCP connector available here is read-only (cannot generate), the
SDK has no cost-estimate or idempotency features, and the application/endpoint id must be configured from your
account. The local pipeline never requires Higgsfield.

## 7. Remotion improvements

Motion grammar (ENTER/EMPHASIZE/CONNECT/EXIT + camera) with named, parameterised behaviours and shared easing/duration/
spring tokens; 8 WCAG-checked themes; 8 semantic layouts (25 + generated total); meaning-driven layout choice with
recorded reasons; complex visuals hold for the whole line; presenter only when motivated; cinematic footage composited
under accurate typography with theme grading and clip-length stretching; captions bounded by the safe area; code font
auto-fit; strict TS typecheck (`npm run typecheck`).

## 8. Audio synchronisation

Kokoro timestamps remain the primary source (unchanged). New: pronunciation dictionary that changes speech but not
captions, espeak-ng fallback synthesised per phrase with energy-snapped word boundaries, per-scene sync measurement
(speech-energy coverage), timing source recorded and estimated timings flagged. Heavier aligners evaluated and
documented as optional (`docs/QUALITY_ASSURANCE.md`). Mastering now measures the encoded true peak and corrects AAC
overshoot — Demo A initially failed QA at −0.3 dBTP; repair brought it to −1.8 dBTP.

## 9. QA results (demo videos)

| Demo | Mode | Length | Theme | Technical pass | Visual issues | Audio score | Repairs |
|---|---|---|---|---|---|---|---|
| A — 3 developer tools | local | 34.1 s | minimal-white | yes (after repair) | 0 (4 before) | 89 | 1: re-master + 4 headings shortened |
| B — How AI agents use tools | claude (interactive storyboard) | 41.8 s | midnight | yes | 0 | 100 | 0 |
| C — Future of AI-powered coding | hybrid (mock footage) | 27.7 s | cinematic-dark | yes | 0 | 100 | 0 |

Scores carry their basis in each `qa/summary.md`; narrative coherence is always "manual review required".
Demo A's audio 89 = one scene's caption-sync heuristic below 0.8 with the espeak fallback voice.

## 10. Cost-control results

`tests/test_v2_providers.py` (all pass): paid disabled by default; explicit policy requires approval and respects the
approved job budget; unknown cost requires a per-request approval and reserves its cap; per-video and daily caps;
release on pre-billing failure; **16 reservations from 8 concurrent processes against a $1.00 daily cap → exactly
$0.90 granted**; Claude gate reconciles real usage; cinematic cache reuse costs $0; missing approval → Remotion
fallback (or pause); exhausted budget → fallback; unknown submit outcome kept and never resubmitted; crash between
submit and record → reconciled, not resubmitted. Demo C: 2 × 4 s mock clips reserved/committed $0.40 against a $0.50
approval — **ledger entries for the mock provider, no money spent**; the second C run reused both clips from cache
(0 new reservations).

## 11. Demo videos

| Demo | Job | File |
|---|---|---|
| A | `2a942ed0a36e` | `data/jobs/2a942ed0a36e/video.mp4` (+ `qa/contact_sheet.jpg`) |
| B | `a87049d2f16a` (final; `d9639996201e` was the run before the hero-word fix) | `data/jobs/a87049d2f16a/video.mp4` |
| C | `617ec360cfea` (first run), `b1fb59493855` (cache re-run: $0, 0 new reservations) | `data/jobs/<id>/video.mp4` |
| Dry run | `02ada942bd34` (CLAUDE mode requested → no key → Ollama absent → template; storyboard + estimate, no render, $0) | `data/jobs/02ada942bd34/storyboard.json` |

Measured wall-clock on 4 vCPU (espeak voice): A 313 s incl. repair render, B 198 s, C 183 s first run / 139 s cached
(render 113–158 s, QA 22–37 s, narration ≈ 2 s, mock footage 31 s).

`data/` is git-ignored; copies of the final MP4s and contact sheets are attached to the delivery message, not committed.

## 12. Tests

```
.venv/bin/python -m pytest -q                         # 93 passed, 1 skipped (the opt-in render)
RUN_SLOW=1 .venv/bin/python -m pytest -q -k end_to_end   # real local render of the V1 example plan: passed (67 s)
npm run typecheck                                     # strict tsc: clean
```

## 13. Remaining limitations

* No live Claude or Higgsfield call was made (credentials/credits/approval); both are mock-tested.
* Kokoro and Ollama could not be installed in the build container (Hugging Face / Ollama hosts blocked), so all demos
  use the espeak-ng voice and the template/interactive scripts. On the Mac, Kokoro and Ollama are used automatically.
* Live GitHub/RSS discovery was blocked in the container; Demo A used operator-supplied README-level notes and says so.
* Repairs re-render the whole video (narration and footage reused); frame-range partial renders are not implemented.
* No vision-model review; no bundled forced aligner; `freezedetect` is the only motion-quality measurement.
* Template-writer headlines are plain and can read as fragments; it is the zero-model fallback.
* Remotion render time dominates (≈2–5 min per 30–40 s reel on 4 vCPU); Apple Silicon timings were not measured.

## 14. Running the upgraded system

```sh
cd /Users/priyanshupatel/Downloads/VIDEOS/local-video-mcp
git fetch origin && git checkout claude/hybrid-video-v2
.venv/bin/pip install -r requirements.lock.txt && .venv/bin/pip install -e . --no-deps
.venv/bin/pip install -r requirements-claude.lock.txt   # optional (CLAUDE/HYBRID)
npm ci && npm run typecheck
.venv/bin/python -m pytest -q
.venv/bin/local-video health
.venv/bin/python examples/demos/demo_a_local.py   # LOCAL; poll with: .venv/bin/local-video status <id>
```
Then reload the MCP host; the server name and launcher are unchanged. For CLAUDE/HYBRID follow
`docs/CLAUDE_INTEGRATION.md`, `docs/HIGGSFIELD_INTEGRATION.md` and `docs/COST_CONTROLS.md`.

## V2.1 — review notes on a locally generated reel

Applied to the V2 renderer: bold frame-0 hook (`hookBold`, prompts and template writer require a bold count/payoff
statement), moving repo visuals (`readmeScroll`, `repoConnect`, floating cards with topic marquee; filler cuts reduced),
phone-size type (≥ 36 px body enforced by QA and a test), and a recap → big call-to-action ending (`outroCTA`; a bug where
a single-beat outro was swallowed by the loop-back was found in the demo and fixed). HYBRID adds an establishing shot
behind the hook; `import_motion_clip` brings exported motion clips (e.g. from Claude's motion tools) into scenes.
Demo D (`data/jobs/3c5f0c05aad4`, 36.9 s, carbon, mock footage under the hook) uses the four repos from the reviewed reel,
with text transcribed from that reel: 0 QA issues, −13.7 LUFS, −1.8 dBTP. Tests: 98 passed, 1 skipped.
Note: the reviewed reel's renderer (dark "FIELDNOTES / product notes" style) is not in the GitHub repository; it exists only
on the user's machine and must be pushed before V2 can be merged with it.
