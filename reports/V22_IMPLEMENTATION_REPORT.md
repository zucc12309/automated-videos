# V2.2 implementation report — FIELDNOTES premium + recurring character

Branch: `claude/hybrid-video-v2` (not merged to main).

V2.2 refines V2/V2.1 rather than rebuilding them. Orchestration, cost control, approvals, the asset cache, job state, MCP tools,
autopilot and QA/repair are unchanged in behaviour. The studio renderer still works through `production.style: "studio"`.

## What was built (by phase)

| Phase | Result | Where |
|---|---|---|
| 0 Audit | Reference A frame analysis, a preserve / replace / merge table, exact steps to import the Mac renderer, and voice evidence | `reports/V22_VISUAL_GAP_AUDIT.md` |
| 1 Design system | `fieldnotes-premium` tokens; the premium Remotion renderer; open-licensed bundled fonts | `brand/tokens.json`, `src/premium/`, `public/fonts/`, `docs/PREMIUM_DESIGN_SYSTEM.md` |
| 2 Character | Versioned identity (12 states, gestures, scales, placement rules, three signatures); SVG character; configurable public name (null) | `brand/character/identity.json`, `src/premium/Blob.tsx`, `docs/CHARACTER_IDENTITY.md` |
| 3 Hook | Three truthful candidates, scored on six criteria; hype or unsourced numbers disqualify; frame-0 readable hook | `video_mcp/creative/hooks.py`, `storyboard.hook_candidates` |
| 4 Motion primitives | 13 semantic primitives mapped onto premium objects; the router records why each layout fits | `src/premium/Objects.tsx`, `beats[].layoutReason` |
| 5 Visual director | Continuity transitions, rhythm (1.6 s minimum hold), character staging with reasons, one reveal reaction | `video_mcp/creative/visual_director.py`, `beats[].direction` |
| 6 Mobile typography | Hook 104–118, headings ≥ 64, body ≥ 40, headline 60, meta ≥ 32 (code 30–40, documented exception); checked automatically | `video_mcp/quality/premium_checks.py`, `tests/test_v22.py` |
| 7 `vibe_coding` | Curated tip library, deterministic six-scene storyboard, prompt / code / guide / DM resources | `video_mcp/content/vibe_library.json`, `director.vibe_storyboard`, `docs/CONTENT_FORMATS.md` |
| 8 CTA engine | LINK / PROMPT / GUIDE / CODE / TOOLS; truthful narration; DM delivery off; resources for manual sending | `video_mcp/creative/cta.py`, `brand/cta_templates.json`, `docs/CTA_RESOURCE_WORKFLOW.md` |
| 9 Preserve infra | Pipeline stages, budget gate, approvals, cache and journal untouched; the supplied-storyboard path also gets the CTA pass | `video_mcp/orchestration/pipeline.py` |
| 10 Brand package | Tokens, character, voice, motion, series labels, CTA templates, reference stats | `brand/` |
| 11 Reference QA | Pixel statistics against Reference A plus a side-by-side sheet; premium brand checks; no model judgments | `video_mcp/quality/reference_compare.py`, `premium_checks.py` |
| 12 Demos | A–D rendered through the real pipeline (see below) | `demos/v22/`, `examples/demos/v22/` |
| 13 Tests | 23 new V2.2 tests (incl. audio profile); full suite 122 passed, 1 skipped | `tests/test_v22.py` |

## Reference audio profile (follow-up request)

You asked for the reference video's audio profile. `video_mcp/audio_profile.py` measures Reference A and stores the result in
`brand/audio_profile.json` (`narration.audio_profile: "reference"` is the default; set it to `"off"` for the V2 sound). Every render is
then compared against the reference, and the result is written to `qa/audio_profile_compare.json`.

| Property | Reference A | Before | After (demo B) | How it is matched |
|---|---|---|---|---|
| Loudness | −14.1 LUFS, −1.6 dBTP | −13.8 LUFS | −14.0 LUFS, −1.7 dBTP | linear gain + limiter. The old single-pass `loudnorm` was dynamic and lifted every pause (floor 13 dB under the voice vs. 28 in the reference) |
| Music bed level | 22.2 dB under speech | 24–27 dB, uneven | 22.3 dB | bed gain computed from the actual narration level (`bed_gain_db`) |
| Music bed character | warm low pad, centroid ~355 Hz, no drums | lo-fi pad + kick + hats + plucks | warm pad, 321 Hz | new `warm_pad` bed: 130–500 Hz chords, soft root, filtered, slow cross-fades |
| Voice pitch | median 118.5 Hz, 93–144 Hz | 102 Hz, 88–114 Hz (monotone) | 118.5 Hz, 89–147 Hz | espeak SSML prosody (+14% pitch, x-high range), calibrated |
| Voice tone (bands vs. total) | low −4.1 / mid −2.8 / presence −12.7 / air −16.7 dB | low −7.4, presence −10.8 | within 0.5 dB | adaptive matching EQ per narration (±6 dB clamp) |
| Pauses / speech share | 0.32 s median, 66% speech | 0.19 s, 80% | about 0.33 s, about 64% | espeak phrase pauses + scene tails from the profile |

**Not matched: the voice's timbre.** Reference A is Kokoro `am_adam`. On your Mac, Kokoro `am_adam` produces that timbre itself, and the
profile then only sets the mix, the EQ trim, the bed and mastering. In this container the espeak fallback now has the reference's pitch,
range, pacing and tonal balance, but it still sounds synthetic. No measurement here can make espeak sound like Kokoro.

## Problems found by looking at the renders, and fixed

Unit tests did not catch any of these. All came from inspecting frames, and each now has a fix and, where possible, a test.

1. Markdown `- ` list lines in code cards were drawn as diff removals (red strikethrough). Diffs are now detected only when declared or
   when both `+ ` and `- ` lines are present.
2. Already-spoken headline words faded back out. Remotion `interpolate` with an easing function and unclamped extrapolation drives the
   eased value negative, so the extrapolation is now clamped.
3. Hub, list and node labels were cut off with "…". They now wrap, with wider limits.
4. The CTA quote marks wrapped onto their own lines. The keyword line is now sized to stay on one line.
5. The vibe demo lost both of its key visuals:
   - The weak prompt was routed to a warning card. The terminal layout required two or more points.
   - The before/after card was replaced by a word tile. The router ignored `prompt_before`/`prompt_after`, and QA's repair pass swapped
     out the layout over a 2-character overflow.

   Fixes: authored layouts whose data requirements are met now win over keyword guesses; prompt pairs count as comparison data;
   template lines may run to 60 characters and wrap.
6. The loop tail dissolved the hook over the CTA. It is now a hard cut, and a cut hides the outgoing beat immediately.
7. Two "big" character reactions in one video (an automatic surprise plus a storyboard celebration). The automatic reveal now yields
   to a storyboard-requested one, and QA counts both kinds.
8. Small text: masthead and meta raised to 32 px, terminal to 40, browser title to 64, phone notice body to 40.

## Demos

Measured values from each demo's `summary.json`, `qa/summary.json` and `costs.json`.

| Demo | Topic | Mode | CTA | Duration | Wall time | QA issues | Brand checks | Reference style (ground / luma / change rate) | Spend |
|---|---|---|---|---|---|---|---|---|---|
| A | 4 Claude Code repos (roundup) | local | LINK | 36.9 s | 184.4 s | 0 | 100 | pass / pass / pass | $0 |
| B | Vibe prompt before/after | local | PROMPT | 25.9 s | 275.0 s | 0 | 100 | pass / pass / pass | $0 |
| C | MCP architecture | local | GUIDE | 36.5 s | 180.5 s | 0 | 100 | pass / pass / pass | $0 |
| D | Future of AI-assisted development | hybrid (MOCK cinematic) | GUIDE | 26.7 s | 160.1 s | 0 | 100 | pass / pass / pass | $0 |

Notes on the table:

- **A** is marked `degraded: [scene_001]`. Its storyboard requests cinematic footage for the hook, and `local` mode renders that
  scene in Remotion instead. The fallback is recorded in `decisions.json`.
- **D** shows $0 because both mock clips were served from the content-addressed asset cache (2 hits). An uncached mock run reserves
  the configured mock rate in the ledger.
- **Source reliability:**
  - A: 100 (GitHub metadata).
  - B: 40 (editorial tips, labelled interpretation).
  - C: 80 (one source; one sentence auto-classified as interpretation).
  - D: 0 (opinion piece with no sources; every line is interpretation and is labelled as such).

All four ran in `local` mode except D. D ran in `hybrid` with the **mock cinematic provider**: local FFmpeg clips stand in for Higgsfield
footage, so D is not live-provider-tested. No paid call was made and no money was spent. Claude direction was not used: no API key is
configured, and storyboards A, C and D are supplied files written in this session. The narration voice in this container is espeak-ng
(see Limitations).

Each `demos/v22/<X>/` contains:

| File | Contents |
|---|---|
| `poster.jpg` | poster frame |
| `contact_sheet.jpg` | 12 frames |
| `storyboard.json` | storyboard, with `hook_candidates` and `cta` |
| `decisions.json` | provider decisions |
| `verification.json` | claim checks |
| `props.json` | per beat: layout reason, transition, character staging and reasons |
| `qa/` | technical, visual, audio, `reference_compare.json`, `reference_side_by_side.jpg`, summary |
| `resources/` | manifest, guide, DM text, plus prompt / code where relevant |
| `costs.json`, `estimate.json`, `timings.json`, `summary.json` | cost and timing |

The MP4 is kept locally (`*.mp4` is gitignored); regenerate it with `examples/demos/v22/run_demo.py`.

## Limitations (stated plainly)

- **Voice.** Reference A's voice measures as Kokoro `am_adam` (male, F0 ≈ 121 Hz). It is pinned in `brand/voice.json` and is the
  config voice on your Mac. This container cannot load Kokoro weights: Hugging Face is blocked, and a third-party npm mirror was
  refused as untrusted. So the demo renders here use the espeak-ng fallback and sound robotic. Rendering on the Mac uses `am_adam`
  automatically. To get Kokoro here, provide the weights through a source you trust, or approve that mirror explicitly.
- **Mac renderer.** The FIELDNOTES renderer that produced Reference A is not in git. V2.2 reconstructs it from the video. It matches on
  the measured statistics (ground colour, luminance, change rate) and passes a visual check of the character sheet, but it is not
  identical code. Push the Mac files (steps in the audit) for an exact merge.
- **Taste and retention.** QA measures readability, consistency, pacing and truthfulness. It cannot judge whether a reel is engaging,
  and no retention or virality claims are made. Narrative coherence is left for manual review.
- **Hook scoring** is a transparent heuristic, not a trained model.
- **Source reliability** for `vibe_coding` scores low (40) by design. The tips are editorial guidance, labelled "interpretation", not
  verified facts.
- **CTA fulfilment** is manual: there is no DM integration, and none is simulated.
- **Higgsfield.** The live path is the V2 adapter. It still requires your API key, a verified price and explicit approval, and was not
  exercised here.
- **Production readiness.** Passing unit tests does not mean production-ready. Review the MP4s on a phone before posting.

## Mac setup / run

```sh
cd /Users/priyanshupatel/Downloads/VIDEOS/local-video-mcp
git fetch origin && git checkout claude/hybrid-video-v2
npm ci                                       # adds @remotion/fonts (fonts themselves are in public/fonts)
.venv/bin/pip install -e . --no-deps         # existing venv; no new Python dependencies
.venv/bin/python -m pytest -q                # expect 122 passed, 1 skipped
# Render the four demos (Kokoro am_adam is used automatically on the Mac):
.venv/bin/python examples/demos/v22/run_demo.py A B C D
open demos/v22/A/video.mp4
# Normal use: MCP tools / autopilot now default to style "premium", theme "fieldnotes-premium".
# Switch back to the V2 look per run: production.style = "studio" in config.json.
```

Optional: `npx remotion still src/index.tsx BlobSheet out/blob.png` renders the character sheet (all states).
