# QA summary

**Technical pass:** yes

| Category | Score | Basis |
|---|---|---|
| technical correctness | 100 | deterministic |
| readability | 100 | deterministic (layout metadata + tokens) |
| visual consistency | 100 | deterministic |
| motion quality | 100 | heuristic (freeze detection only; motion taste needs manual review) |
| scene variety | 100 | deterministic + heuristic |
| brand consistency | 100 | deterministic (character staging, frame-0 hook, CTA, pacing from props + brand/*.json) |
| audio quality | 89 | deterministic loudness/peak; heuristic caption sync |
| narrative coherence | n/a | manual review required (no model opinion collected) |
| source reliability | 40 | deterministic word-overlap support check; share of claims with source support |

## Technical checks (deterministic)

- PASS `readable` — ffprobe parsed the container
- PASS `resolution` — 1080x1920 (want 1080x1920)
- PASS `aspect_ratio` — 9:16
- PASS `frame_rate` — 30.000 fps (want 30)
- PASS `duration` — 23.55s (expected 23.50s)
- PASS `audio_present` — aac 48000
- PASS `decode_integrity` — clean full decode
- PASS `black_frames` — none
- PASS `frozen_frames` — none
- PASS `unexpected_silence` — none

## Visual issues

- none

## Audio

- PASS `loudness` — -14.0 LUFS (target -14.0 ±2) (deterministic)
- PASS `true_peak` — -1.7 dBTP (limit -0.5) (deterministic)
- PASS `clipping` — true peak -1.7 dBTP (deterministic)
- PASS `scene_001_caption_sync` — {'covered_speech': 0.893, 'inside_ratio': 0.908} via energy_snapped (heuristic)
- PASS `scene_002_caption_sync` — {'covered_speech': 0.873, 'inside_ratio': 0.822} via energy_snapped (heuristic)
- PASS `scene_003_caption_sync` — {'covered_speech': 0.815, 'inside_ratio': 0.8} via energy_snapped (heuristic)
- PASS `scene_004_caption_sync` — {'covered_speech': 0.841, 'inside_ratio': 0.79} via energy_snapped (heuristic)
- FAIL `scene_005_caption_sync` — {'covered_speech': 0.697, 'inside_ratio': 0.814} via energy_snapped (heuristic)
- PASS `scene_006_caption_sync` — {'covered_speech': 0.899, 'inside_ratio': 0.885} via energy_snapped (heuristic)
- Caption timings are **estimated** (no model timestamps for this voice).

## Sources

Claim status counts: {'verified': 2, 'interpretation': 3, 'unverified': 0, 'removed': 0}

## Manual review required

- Factual accuracy against the cited sources
- Pronunciation of names and acronyms
- Overall taste / brand fit
- Music licensing (procedural bed is generated locally)
