# QA · EP. 001 · Script in, short out: an open-source video maker

**Result:** PASS (52 deterministic checks)

- Duration: 25.67s · 51 words · 147.8 wpm while speaking
- Demonstration: **project-showcase**: official output examples published by the project itself (shown muted and credited); the features they show were also verified in source or by a local run (on-screen tag: “OFFICIAL MPT DEMO”)
- Loudness: final -14.2 LUFS / -1.9 dBTP; no-music -14.1 LUFS / -2.0 dBTP
- Visual review: reviewed (agent inspection of extracted frames, not a computed check)

| Group | Check | Result | Detail |
|---|---|---|---|
| technical:final | readable | pass | ffprobe parsed the container |
| technical:final | resolution | pass | 1080x1920 (want 1080x1920) |
| technical:final | aspect_ratio | pass | 9:16 |
| technical:final | frame_rate | pass | 30.000 fps (want 30) |
| technical:final | duration | pass | 25.67s (expected 25.67s) |
| technical:final | audio_present | pass | aac 48000 |
| technical:final | decode_integrity | pass | clean full decode |
| technical:final | black_frames | pass | none |
| technical:final | frozen_frames | pass | none |
| technical:final | unexpected_silence | pass | none |
| technical:final | codecs | pass | {'video': 'h264', 'audio': 'aac'} |
| audio:final | loudness | pass | -14.2 LUFS (target −14 ±0.5) |
| audio:final | true_peak | pass | -1.9 dBTP (≤ −1.0, no clipping) |
| technical:no_music | readable | pass | ffprobe parsed the container |
| technical:no_music | resolution | pass | 1080x1920 (want 1080x1920) |
| technical:no_music | aspect_ratio | pass | 9:16 |
| technical:no_music | frame_rate | pass | 30.000 fps (want 30) |
| technical:no_music | duration | pass | 25.67s (expected 25.67s) |
| technical:no_music | audio_present | pass | aac 48000 |
| technical:no_music | decode_integrity | pass | clean full decode |
| technical:no_music | black_frames | pass | none |
| technical:no_music | frozen_frames | pass | none |
| technical:no_music | unexpected_silence | pass | none |
| technical:no_music | codecs | pass | {'video': 'h264', 'audio': 'aac'} |
| audio:no_music | loudness | pass | -14.1 LUFS (target −14 ±0.5) |
| audio:no_music | true_peak | pass | -2.0 dBTP (≤ −1.0, no clipping) |
| pacing | duration | pass | 25.67s (series range 22–28s) |
| pacing | speaking_rate | pass | 148 wpm while speaking (51 words / 20.70s measured audio; target 145–165) |
| timing | scene_fits_narration:hook | pass | 113 frames for 102 frames of lead + speech |
| timing | scene_fits_narration:discovery | pass | 88 frames for 77 frames of lead + speech |
| timing | scene_fits_narration:demo | pass | 213 frames for 198 frames of lead + speech |
| timing | scene_fits_narration:tech | pass | 129 frames for 115 frames of lead + speech |
| timing | scene_fits_narration:payoff | pass | 167 frames for 151 frames of lead + speech |
| subtitles | transcript_match | pass | 51 subtitle words vs 51 narrated words |
| subtitles | group_size | pass | 2–5 words per group (2 short groups at sentence ends) |
| subtitles | readable_time | pass | shortest group 0.54s on screen (≥ 0.45 s) |
| subtitles | no_overlap | pass | groups never overlap in time |
| subtitles | sync | pass | first subtitle at 0.05s; word timing source: energy_snapped (sentence boundaries exact, words inside a sentence estimated) |
| subtitles | safe_zone | pass | band y 1420–1572 inside 220–1620 |
| subtitles | clear_of_demo | pass | subtitle band clears every demo / text block |
| layout | blocks_in_safe_zone | pass | all blocks inside the video safe zone |
| hook | frame0_contrast | pass | luma p99–p5 spread 230 on frame 0 (demo + headline visible immediately) |
| motion | motion_share | pass | 96% of 0.25 s steps change visibly |
| motion | longest_static | pass | longest static stretch 0.50s (≤ 1.5 s) |
| brand | palette_share | pass | 99.8% of sampled pixels on the series palette or its blends |
| cover | sizes | pass | {'episode-001-cover.png': (1080, 1920), 'episode-001-cover-4x5.png': (1080, 1350), 'episode-001-cover-square.png': (1080, 1080)} |
| cover | crop_safe | pass | essential elements span x 124–977, y 463–1454; 0 px outside the square safe region x 60–1020, y 420–1500 (survives 9:16, 4:5 and 1:1) |
| cover | text_not_clipped | pass | no essential pixel touches the side margins |
| cover | episode_number_thumbnail | pass | EP label cap height ≈ 17 px in a 357 px grid tile (≥ 12 px); see qa/cover-grid-thumbnail.png |
| cover | headline_largest | pass | headline 146 px vs EP label 72 px and header 32 px |
| mascot | single_source | pass | series mascot = src/devmimo/Mimo.tsx (brand/character/identity.json); not redrawn or regenerated |
| copy | claims_and_phrases | pass | every on-screen label cites a verified feature; no banned phrases or repository statistics |

## Visual review

- Frame 0 opens on the demonstration: MoneyPrinterTurbo's WebUI fields (topic and script) beside its real output playing in a phone, with 'SCRIPT IN.' on screen. No logo intro.
- Discovery: series header, EP. 001 and the harry0703 / MoneyPrinterTurbo card. Mimo (300 px) rises from a hairline, surprised, then points at the card. Fixed: Mimo covering 'found this.' and the card's last line.
- Demo: terminal of real run-log stages beside final-1.mp4. VOICE / SUBTITLES / MUSIC / EDIT chips land in order on the spoken words. Mimo nods on each chip and turns happy on the last. Fixed: one terminal line clipping at 24 px (now 22 px).
- Flow: TOPIC → SCRIPT + VOICE → FINISHED SHORT. Mimo walks down the nodes and turns happy at the end.
- Payoff: the output replays. Mimo is excited and 'WOULD YOU TRY THIS?' is on screen, with the 'EP. 001 — SAVED TO MIMO'S FINDS' stamp on 'Follow'. 2 s outro with 'FOLLOW @devmimo · EP. 002 SOON'.
- Subtitles stay in the band at y 1420 and never cover the demo. Inside the phone, MoneyPrinterTurbo's own burned subtitles are visible (they are part of its output).
- Cover: fixed the phone overlapping 'SHORT OUT.' (the illustration now starts below the measured headline). The real WebUI crop, the real output frame and Mimo all sit inside the square safe region. EP. 001 is legible in the 357 px grid tile.
- Fixed earlier in this pass: the hook WebUI was unreadable (a full-column screenshot), so it was re-captured at a 380 px viewport and cropped to the topic and script fields.
