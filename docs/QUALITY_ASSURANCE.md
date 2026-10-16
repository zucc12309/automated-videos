# Quality assurance

QA inspects the rendered file, not the plan. Every check is labelled with its basis:
**deterministic** (a measurement), **heuristic** (rule of thumb on pixels/energy), **model opinion** (only if an
optional vision review is added; none is collected by default), or **manual review required**.

## Technical (`quality/video_validation.py`, deterministic)

ffprobe readable · resolution · aspect ratio · frame rate · duration vs. composition (±0.6 s) · audio stream · full
decode without errors · black frames (`blackdetect`, 0.3 s, 99.5 % of pixels below 5 % luma — dark themes sit above
the floor) · frozen frames ≥ 3.5 s (`freezedetect`, advisory) · unexpected silence ≥ 1.2 s before the tail
(`silencedetect`, advisory).

## Audio (`quality/audio_analysis.py`)

EBU R128 integrated loudness (target −14 LUFS ± 2), true peak ≤ −0.5 dBTP (mandatory), clipping, per-scene caption
sync (share of speech energy covered by caption word spans ≥ 0.8; deterministic for Kokoro timestamps, heuristic for
estimated timings). Mastering measures the encoded true peak and corrects AAC overshoot (found and fixed during
Demo A: −0.3 → −1.8 dBTP).

## Visual (`quality/frame_analysis.py`)

Deterministic, from `props.json` + `themes.json` (no OCR): stage inside safe area · theme contrast · text longer than
a layout's capacity (would be ellipsis-clipped) · font sizes · code font after auto-fit · presenter occlusion ·
layout without its data (empty recap/hook stack, repo card without API data) · cinematic layout without footage ·
caption band height · back-to-back layouts · layout variety · single theme.

Heuristic, from sampled frames (first, every scene entrance/middle/exit, every beat boundary, last): near-uniform
stage mid-scene (missing content) · consecutive scenes with near-identical frames. Frames go to `qa/frames/` and a
contact sheet to `qa/contact_sheet.jpg`.

## Scores and reports

`qa/summary.md|json`: technical correctness, readability, visual consistency, motion quality (freeze-based only),
scene variety, audio quality, narrative coherence (manual), source reliability (share of claims with source support),
each with its basis; plus `technical.json`, `visual.json`, `audio.json`, `storyboard.json`, `repairs.json`.

## Repair loop

`quality_report.plan_repairs` maps issues to targeted overrides, applied to the affected scenes only:

| Issue | Repair |
|---|---|
| text too long for its layout (heading/points/label) | shorten at a word boundary to that layout's capacity |
| other overflow, tiny text, blank stage | avoid those layouts for that scene |
| presenter occlusion | hide presenter for the scene |
| missing footage | drop media → approved fallback layout |
| repetition | re-seed layout planning |
| contrast | switch to carbon |
| true peak / loudness / clipping | re-master only (no re-render) |

At most `quality_control.max_repairs` attempts (default 2). If mandatory checks still fail the job ends **FAILED** with
the reasons; it is never reported as success. `repair_video` re-runs the loop on an existing job; `review_video`
re-runs QA only. Re-rendering is whole-video (narration, footage and layout plan are reused); frame-range partial
renders are not implemented.

## Alignment

Kokoro provides per-token timestamps (model-derived). The espeak fallback synthesises phrase by phrase (exact phrase
boundaries), estimates word spans by syllables and snaps boundaries to energy minima. Evaluated but not bundled:
WhisperX (good accuracy; needs a ~1.5 GB model + torch), Montreal Forced Aligner (excellent, but a conda environment and
acoustic models), ctc-forced-aligner / torchaudio MMS (good, ~1 GB weights, GPU-friendly). On a 24 GB Apple Silicon Mac
any of them is feasible as an optional plug-in, but none is required because Kokoro already supplies timestamps.
`provenance.json → caption_timing` and the QA report state which source was used; estimated timings are flagged.

## Manual review always required

Factual accuracy against cited sources · pronunciation of names and acronyms · overall taste / brand fit.
