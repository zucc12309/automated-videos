# QA · EP. 002 · 7 Adobe-style apps rebuilt with AI, and the tool that helps agents understand apps

**Result:** PASS (70 deterministic checks)

- Duration: 31.50s · 73 words · 160.1 wpm while speaking
- Demonstration: **captured**: a real screen/webcam capture of the project running
- Loudness: final -14.2 LUFS / -1.9 dBTP; no-music -14.2 LUFS / -1.8 dBTP
- Instagram safe area: top 250, bottom 400, left 60, right 180 px (previews: qa/instagram-safe-preview.png)
- Visual review: inspected (agent review of contact sheet, Instagram-overlay previews, hook strips, cover crops and key frames); narration not auditioned by a human ear

| Group | Check | Result | Detail |
|---|---|---|---|
| technical:final | readable | pass | ffprobe parsed the container |
| technical:final | resolution | pass | 1080x1920 (want 1080x1920) |
| technical:final | aspect_ratio | pass | 9:16 |
| technical:final | frame_rate | pass | 30.000 fps (want 30) |
| technical:final | duration | pass | 31.50s (expected 31.50s) |
| technical:final | audio_present | pass | aac 48000 |
| technical:final | decode_integrity | pass | clean full decode |
| technical:final | black_frames | pass | none |
| technical:final | frozen_frames | pass | none |
| technical:final | unexpected_silence | pass | none |
| technical:final | exact_1080x1920 | pass | 1080x1920 |
| technical:final | codecs | pass | {'video': 'h264', 'audio': 'aac'} |
| audio:final | loudness | pass | -14.2 LUFS (target −14 ±0.5) |
| audio:final | true_peak | pass | -1.9 dBTP (≤ −1.0, no clipping) |
| technical:final | no_black_frames | pass | no black frames (blackdetect ≥ 0.05 s) |
| technical:no_music | readable | pass | ffprobe parsed the container |
| technical:no_music | resolution | pass | 1080x1920 (want 1080x1920) |
| technical:no_music | aspect_ratio | pass | 9:16 |
| technical:no_music | frame_rate | pass | 30.000 fps (want 30) |
| technical:no_music | duration | pass | 31.50s (expected 31.50s) |
| technical:no_music | audio_present | pass | aac 48000 |
| technical:no_music | decode_integrity | pass | clean full decode |
| technical:no_music | black_frames | pass | none |
| technical:no_music | frozen_frames | pass | none |
| technical:no_music | unexpected_silence | pass | none |
| technical:no_music | exact_1080x1920 | pass | 1080x1920 |
| technical:no_music | codecs | pass | {'video': 'h264', 'audio': 'aac'} |
| audio:no_music | loudness | pass | -14.2 LUFS (target −14 ±0.5) |
| audio:no_music | true_peak | pass | -1.8 dBTP (≤ −1.0, no clipping) |
| technical:no_music | no_black_frames | pass | no black frames (blackdetect ≥ 0.05 s) |
| pacing | duration | pass | 31.50s (episode range 26–33s; brief arc ≈ 31 s) |
| pacing | speaking_rate | pass | 160 wpm while speaking (73 words / 27.36s; target 150–175) |
| timing | beat_fits_narration:shock | pass | 106 frames for 100 frames of lead + speech |
| timing | beat_fits_narration:context | pass | 125 frames for 119 frames of lead + speech |
| timing | beat_fits_narration:mystery | pass | 104 frames for 77 frames of lead + speech |
| timing | beat_fits_narration:discovery | pass | 108 frames for 101 frames of lead + speech |
| timing | beat_fits_narration:proof | pass | 222 frames for 204 frames of lead + speech |
| timing | beat_fits_narration:possibility | pass | 158 frames for 131 frames of lead + speech |
| timing | beat_fits_narration:question | pass | 122 frames for 106 frames of lead + speech |
| timing | no_awkward_pauses | pass | longest silence after a beat's narration: 0.90s (mystery; ≤ 1.6 s) |
| ending | ends_on_question | pass | reel ends 0.59s after the last word of the question beat; no outro |
| subtitles | transcript_match | pass | subtitle words = narrated words |
| subtitles | group_size | pass | 1–5 words per group |
| subtitles | readable_time | pass | shortest group 0.48s on screen (≥ 0.45 s) |
| subtitles | no_overlap | pass | groups never overlap in time |
| subtitles | sync | pass | first subtitle at 0.05s, first word at 0.05s; timing source energy_snapped |
| subtitles | emphasis | pass | orange words: Adobe-style, Engineer, GitHub, Reverse, code,, code., engineer?, reverse, seven, source |
| subtitles | above_caption_ui | pass | band x 60–900, y 1372–1504 inside safe x 60–900, y ≤ 1520 |
| subtitles | clear_of_content | pass | subtitle band clears every content block |
| layout | safe_area_matches_config | pass | layout safe area x 60–900, y 250–1520 = margins top 250, bottom 400, left 60, right 180 |
| layout | blocks_in_safe_area | pass | header, hook, demo, repository, subtitles and CTA blocks inside the safe area |
| layout | instagram_previews | pass | qa/instagram-safe-preview.png and qa/instagram/*.png (simulated Reels UI) |
| hook | starts_with_result | pass | frame 0 shows a real recreation screenshot (no logo, title card or fade) |
| hook | premise_on_frame0 | pass | “7 ADOBE APPS.” is on screen from frame 0; “REBUILT WITH AI?” lands with the narration |
| hook | frame0_contrast | pass | luma p99–p5 spread 228 on frame 0 |
| hook | variant_a | pass | episode-002-hook-a.mp4: 4.70s, “Someone recreated seven Adobe-style apps using AI.” |
| hook | variant_b | pass | episode-002-hook-b.mp4: 5.37s, “People are rebuilding software that used to take entire teams to make.” |
| hook | variant_c | pass | episode-002-hook-c.mp4: 4.80s, “There's a GitHub project that helps AI figure out how apps work.” |
| motion | motion_share | pass | 77% of 0.25 s steps change visibly |
| motion | longest_static | pass | longest static stretch 1.50s (≤ 1.5 s) |
| brand | palette_share | pass | 99.4% of sampled pixels on the series palette (third-party screenshots are shown as they are) |
| cover | sizes | pass | {'episode-002-cover.png': (1080, 1920), 'episode-002-cover-4x5.png': (1080, 1350), 'episode-002-cover-square.png': (1080, 1080)} |
| cover | crop_safe | pass | 0 essential px outside the square safe region (survives 9:16, 4:5 and 1:1) |
| cover | few_large_previews | pass | 3 interface previews (2–3, not seven tiny ones) |
| cover | headline_thumbnail | pass | headline 115 px → 38 px in a 357 px grid tile (≥ 28) |
| copy | claims_and_phrases | pass | every on-screen claim cites a verified feature; no banned phrases or repository statistics |
| copy | recreations_labelled | pass | every recreation is named and tagged “-style · open source”; hook tag: OPEN-SOURCE RECREATIONS · NOT ADOBE |
| copy | projects_kept_separate | pass | REA card says A DIFFERENT PROJECT; metadata states REA was not used on ArtCraft or Adobe |
| copy | proof_is_real_run | pass | proof + possibility claims come from the captured REA run (evidence/episode-002-rea) |
| mascot | single_source | pass | Mimo = src/devmimo/Mimo.tsx (brand/character/identity.json); unchanged |

## Brief checklist (visual review)

- **1 premise within one second**: yes: frame 0 = PhotoCraft (Great Wave) + 'OPEN-SOURCE RECREATIONS · NOT ADOBE' + '7 ADOBE APPS.'
- **2 authentic, accurately labelled Adobe-style visuals**: yes: ArtCraft's own README screenshots, each named with '<App>-style · open source'; no Adobe UI, icons or logos
- **3 recreations vs REA distinct**: yes: REA card says 'A DIFFERENT PROJECT'; narration never says REA made them; caption explains
- **4 REA demo is genuine evidence**: yes: real MCP calls by a separate agent, real objdump lines, byte-identical rebuild; tagged 'REAL REA RUN · TEST APP MADE FOR THIS DEMO'
- **5 payoff understandable**: yes: input → app output, agent findings in plain English, ORIGINAL vs AGENT'S REBUILD with '0 BYTES DIFFERENT'
- **6 every scene advances the story**: yes: 7 beats, each 3.3–7.4 s, no repeated content
- **7 subtitles readable on a phone**: yes: 50 px, 3–5 words, orange emphasis on seven/Adobe/GitHub/Reverse Engineer/source code
- **8 important visuals inside safe zones**: yes: qa/instagram-safe-preview.png; all blocks inside x 60–900, y 250–1520
- **9 Mimo consistent**: yes: src/devmimo/Mimo.tsx only — surprised (hook), curious (mystery), excited (repo), thinking (proof), pointing (question)
- **10 cover readable in grid view**: yes: qa/cover-grid-thumbnail.png — EP. 002 and headline legible at 357 px
- **11 ending short**: yes: question + FOLLOW @DEVMIMO, reel ends 0.55 s after the last word; no outro
- **12 export exactly 1080x1920**: yes: both exports and all hook previews (ffprobe)
- **13 audio/subtitles synchronized**: yes by construction (subtitles from the TTS word timings; first subtitle within 0.15 s of first word); not auditioned by ear
- **14 black frames / clipped text / awkward pauses**: none found: blackdetect clean; longest post-narration silence ≤ 1.6 s check passes
- **15 project claims verified**: yes: every on-screen claim cites a verified feature (spec validation); research.md maps each line to evidence

## Visual review findings

- Narration speed 1.0 (160 wpm). Kokoro pronunciation of 'Adobe-style' and 'Premiere' has not been checked by ear.
- Static-looking stretches remain only on reading holds (findings list, 'rebuilding…') and are ≤ 1.5 s.

## Hook choice

- **A · Curiosity (selected)**: real recreation + premise on frame 0, readable without audio, accurate (developer's statement, kept as a question), flows straight into the four app names
- **B · Contrarian**: 'BIG-TEAM SOFTWARE.' is vaguer and a framing rather than a measured fact; weaker without audio
- **C · Discovery**: opens on REA's dense terminal screenshot, unreadable at phone size; the curiosity gap is smaller
