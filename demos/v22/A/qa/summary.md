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
| audio quality | 100 | deterministic loudness/peak; heuristic caption sync |
| narrative coherence | n/a | manual review required (no model opinion collected) |
| source reliability | 100 | deterministic word-overlap support check; share of claims with source support |

## Technical checks (deterministic)

- PASS `readable` — ffprobe parsed the container
- PASS `resolution` — 1080x1920 (want 1080x1920)
- PASS `aspect_ratio` — 9:16
- PASS `frame_rate` — 30.000 fps (want 30)
- PASS `duration` — 37.00s (expected 36.93s)
- PASS `audio_present` — aac 48000
- PASS `decode_integrity` — clean full decode
- PASS `black_frames` — none
- PASS `frozen_frames` — none
- PASS `unexpected_silence` — none

## Visual issues

- none

## Audio

- PASS `loudness` — -13.8 LUFS (target -14.0 ±2) (deterministic)
- PASS `true_peak` — -1.6 dBTP (limit -0.5) (deterministic)
- PASS `clipping` — true peak -1.6 dBTP (deterministic)
- PASS `scene_001_caption_sync` — {'covered_speech': 0.97, 'inside_ratio': 0.811} via energy_snapped (heuristic)
- PASS `scene_002_caption_sync` — {'covered_speech': 0.906, 'inside_ratio': 0.878} via energy_snapped (heuristic)
- PASS `scene_003_caption_sync` — {'covered_speech': 0.92, 'inside_ratio': 0.889} via energy_snapped (heuristic)
- PASS `scene_004_caption_sync` — {'covered_speech': 0.903, 'inside_ratio': 0.841} via energy_snapped (heuristic)
- PASS `scene_005_caption_sync` — {'covered_speech': 0.954, 'inside_ratio': 0.92} via energy_snapped (heuristic)
- PASS `scene_006_caption_sync` — {'covered_speech': 0.879, 'inside_ratio': 0.848} via energy_snapped (heuristic)
- Caption timings are **estimated** (no model timestamps for this voice).

## Sources

Claim status counts: {'verified': 4, 'interpretation': 0, 'unverified': 0, 'removed': 0}

## Manual review required

- Factual accuracy against the cited sources
- Pronunciation of names and acronyms
- Overall taste / brand fit
- Music licensing (procedural bed is generated locally)
