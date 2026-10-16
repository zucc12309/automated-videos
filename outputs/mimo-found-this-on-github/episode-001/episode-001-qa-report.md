# QA · EP. 001 · This GitHub repo turns a topic into a video

**Result:** PASS (52 deterministic checks)

- Duration: 26.57s · 57 words · 158.3 wpm while speaking
- Demonstration: **project-showcase**: official output examples published by the project itself (shown muted and credited); the features they show were also verified in source or by a local run (on-screen tag: “OFFICIAL MPT DEMO”)
- Loudness: final -14.2 LUFS / -1.9 dBTP; no-music -14.2 LUFS / -1.9 dBTP
- Visual review: reviewed (agent inspection of extracted frames, not a computed check)

| Group | Check | Result | Detail |
|---|---|---|---|
| technical:final | readable | pass | ffprobe parsed the container |
| technical:final | resolution | pass | 1080x1920 (want 1080x1920) |
| technical:final | aspect_ratio | pass | 9:16 |
| technical:final | frame_rate | pass | 30.000 fps (want 30) |
| technical:final | duration | pass | 26.57s (expected 26.57s) |
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
| technical:no_music | duration | pass | 26.57s (expected 26.57s) |
| technical:no_music | audio_present | pass | aac 48000 |
| technical:no_music | decode_integrity | pass | clean full decode |
| technical:no_music | black_frames | pass | none |
| technical:no_music | frozen_frames | pass | none |
| technical:no_music | unexpected_silence | pass | none |
| technical:no_music | codecs | pass | {'video': 'h264', 'audio': 'aac'} |
| audio:no_music | loudness | pass | -14.2 LUFS (target −14 ±0.5) |
| audio:no_music | true_peak | pass | -1.9 dBTP (≤ −1.0, no clipping) |
| pacing | duration | pass | 26.57s (series range 22–28s) |
| pacing | speaking_rate | pass | 158 wpm while speaking (57 words / 21.60s measured audio; target 145–165) |
| timing | scene_fits_narration:hook | pass | 124 frames for 113 frames of lead + speech |
| timing | scene_fits_narration:discovery | pass | 76 frames for 66 frames of lead + speech |
| timing | scene_fits_narration:demo | pass | 225 frames for 210 frames of lead + speech |
| timing | scene_fits_narration:tech | pass | 147 frames for 134 frames of lead + speech |
| timing | scene_fits_narration:payoff | pass | 165 frames for 148 frames of lead + speech |
| subtitles | transcript_match | pass | 57 subtitle words vs 57 narrated words |
| subtitles | group_size | pass | 2–5 words per group (1 short groups at sentence ends) |
| subtitles | readable_time | pass | shortest group 0.71s on screen (≥ 0.45 s) |
| subtitles | no_overlap | pass | groups never overlap in time |
| subtitles | sync | pass | first subtitle at 0.05s; word timing source: energy_snapped (sentence boundaries exact, words inside a sentence estimated) |
| subtitles | safe_zone | pass | band y 1420–1572 inside 220–1620 |
| subtitles | clear_of_demo | pass | subtitle band clears every demo / text block |
| layout | blocks_in_safe_zone | pass | all blocks inside the video safe zone |
| hook | frame0_contrast | pass | luma p99–p5 spread 230 on frame 0 (demo + headline visible immediately) |
| motion | motion_share | pass | 90% of 0.25 s steps change visibly |
| motion | longest_static | pass | longest static stretch 1.00s (≤ 1.5 s) |
| brand | palette_share | pass | 100.0% of sampled pixels on the series palette or its blends |
| cover | sizes | pass | {'episode-001-cover.png': (1080, 1920), 'episode-001-cover-4x5.png': (1080, 1350), 'episode-001-cover-square.png': (1080, 1080)} |
| cover | crop_safe | pass | essential elements span x 125–977, y 463–1455; 0 px outside the square safe region x 60–1020, y 420–1500 (survives 9:16, 4:5 and 1:1) |
| cover | text_not_clipped | pass | no essential pixel touches the side margins |
| cover | episode_number_thumbnail | pass | EP label cap height ≈ 17 px in a 357 px grid tile (≥ 12 px); see qa/cover-grid-thumbnail.png |
| cover | headline_largest | pass | headline 150 px vs EP label 72 px and header 32 px |
| mascot | single_source | pass | series mascot = src/devmimo/Mimo.tsx (brand/character/identity.json); not redrawn or regenerated |
| copy | claims_and_phrases | pass | every on-screen label cites a verified feature; no banned phrases or repository statistics |

## Visual review

- Revision 3 (producer notes). Hook: 'THIS GITHUB REPO / TURNS A TOPIC / INTO A VIDEO.' slams line by line on the narration over two official demos playing from frame 0.
- Before → after: a TOPIC card ('The future of everyday robotics', labelled 'title of the official demo') types in. SCRIPT, FOOTAGE, VOICE, SUBTITLES and EDIT tick with spinners and checks on the spoken words. A 'GENERATING…' placeholder turns into the official robotics demo in a large phone (530×940) at FOOTAGE, and it glows when EDIT completes. Mimo goes curious → surprised → happy.
- Readability: repo card owner 42 px, name 82 px, description 44 px, meta 36 px. Flow sublines 30 px, series bug 28 px, phone OUTPUT / OFFICIAL MPT DEMO tags at least 22 / 19 px (scaled with the phone). Stage names 52 px.
- Payoff: 'WOULD YOU LET AI MAKE YOUR NEXT REEL?' is fitted full-width across three balanced lines, with Mimo and the 'SAVED TO MIMO'S FINDS' stamp below.
- Fixed in this revision: the hook peek covered 'REPO' on the 3-line headline (the peek is now skipped for 3-line headlines); the enlarged repo card collided with Mimo (card moved up); the topic text clipped its closing quote (now fitted).
- Cover: 'TOPIC IN. / VIDEO OUT.' over a fan of real demo frames; crop-safe.
- Export: 1080×1920 H.264 at about 6 Mbps, AAC 192 kbps (ffprobe; also the technical/resolution QA check). Lower-resolution copies seen elsewhere are previews, not the deliverable.
