# QA report · I built this game with Claude

29.53 s · 168.0 wpm · final -14.2 LUFS / -1.9 dBTP

**48/49 automated checks pass**, 0 fail, 1 advisory. Visual review: recorded.

## Visual review (frames inspected)

- **Hook: gameplay in the first 0.5 s** — frame 0 is Level 33 mid-run with packages moving; the headline I BUILT THIS GAME / WITH CLAUDE. is already on screen; no logo, terminal or title card
- **Idea: genuine prompt** — verbatim excerpt from the creator's first development prompt types out over the dimmed game, then slides away to Level 1 being solved
- **Prompt → game** — 3 quick cuts: Level 20 taps, Neon Circuit crossing run, Level 36 run
- **Features** — CHARACTERS (The Crew screen), 36 PUZZLES · 5 WORLDS (level list scrolling through all five worlds), HINTS THAT TEACH (Hint 1 of 3 with the highlighted area) — all implemented features, labels large
- **Iteration** — same level, same taps, first playable build (plain package blocks, smaller board) beside the latest build (characters, celebration); labelled FIRST PLAYABLE BUILD / LATEST BUILD
- **Result** — Level 36 delivery + celebration with BUILT WITH CLAUDE. and STILL IN DEVELOPMENT
- **CTA** — COMMENT ‘LINK’ / OR DM ME ‘LINK’ over active gameplay (last taps before Run), small Mimo + @DEVMIMO; no repository mentioned
- **Loop** — the last frame is the same recording 0.03 s before the first frame's moment, so the replay continues the run
- **Instagram safe zones** — headline, card, labels, CTA, Mimo, handle and subtitles all clear of the simulated top bar, action rail and caption block
- **Privacy** — on-screen titles seen: Tri-Color, First Tap, Pair Up, Right of Way, Junction, The Crew, Levels, world names; the level titled with the project's name is cropped below its title bar; home/title screens never used
- **Cover** — real frame (crew celebration) under the two-line statement; checked in all five crops (master, 3:4 grid, 4:5, 1:1, 4:5 used as the 9:16 Reel cover) with nothing cut

### Found and fixed during review

- CTA and 36 PUZZLES · 5 WORLDS plates overflowed the side margins: text now auto-fits the safe width; QA measures the margins on 58 frames
- BUILT WITH CLAUDE. headline never appeared (absolute vs. beat-local frame): fixed
- HINTS THAT TEACH shot lasted ~1 s: beat tail lengthened, now ~1.9 s
- Two cuts would have shown the game's title screen (CTA pre-roll, frame behind the prompt): re-recorded the hook with more taps and moved the reveal
- Levels shot too short for its line: re-recorded with a scroll through all five worlds
- Cover board's bottom row was cut: card proportions changed
- Simulated Instagram caption showed the emoji as a box: stripped for the preview font
- Cover was cut off in Instagram's crops (headline and board ran nearly edge to edge): all content moved into x 180–900, y 430–1490, which the 1:1, 4:5, 3:4 profile-grid and 4:5-as-9:16 crops all keep; added a 3:4 file and a measured QA check

### Not verified

- Narration not listened to by a person (pronunciation of 'Claude', 'DM', 'LINK' unchecked by ear)
- Instagram UI is a simulation, not the real app
- The game itself was recorded in a desktop renderer (Mesa llvmpipe), not on a phone


## technical

| Check | Result | Detail |
|---|---|---|
| final_1080x1920 | PASS | 1080x1920 |
| final_30fps_h264_aac | PASS | h264 30/1 / aac |
| final_duration_25_30s | PASS | 29.53 s |
| no_music_1080x1920 | PASS | 1080x1920 |
| no_music_30fps_h264_aac | PASS | h264 30/1 / aac |
| no_music_duration_25_30s | PASS | 29.53 s |
| no_black_frames | PASS | blackdetect d≥0.1 s: none |

## audio

| Check | Result | Detail |
|---|---|---|
| final_loudness | PASS | -14.2 LUFS, -1.9 dBTP (target −14 LUFS, ≤ −1 dBTP) |
| no_music_loudness | PASS | -14.2 LUFS, -1.9 dBTP (target −14 LUFS, ≤ −1 dBTP) |
| game_sound_is_the_games_own | PASS | SFX layer = the recordings' own audio (taps, belts, deliveries, celebration), cut with the picture |

## pacing

| Check | Result | Detail |
|---|---|---|
| narration_wpm | PASS | 168 wpm while speaking (target 150–175); Kokoro speed 0.838 |
| no_dead_air | PASS | longest gap after a beat's last word: 0.96 s |

## hook

| Check | Result | Detail |
|---|---|---|
| gameplay_at_frame_0 | PASS | first cut: hook @ 6.1 s from frame 0 |
| motion_in_first_0.5s | PASS | mean change in the gameplay card 0→0.5 s: 12.8/255 |
| headline_from_frame_0 | PASS | I BUILT THIS GAME / WITH CLAUDE. (drawn at full opacity from frame 0) |
| no_logo_terminal_or_title_card | PASS | hook is gameplay only |

## footage

| Check | Result | Detail |
|---|---|---|
| game_visible_most_of_reel | PASS | real gameplay unobstructed on 93% of frames (prompt card excluded) |
| every_clip_is_a_recording | PASS | big, c06-new, c06-old, fail_fix, first, hook, menus, neon, solve |
| recorded_with_engine | PASS | Godot 4.5.1 (official Linux build), GL Compatibility renderer, Xvfb + Mesa llvmpipe; touch indicator drawn where each tap lands |

## cuts

| Check | Result | Detail |
|---|---|---|
| fast_purposeful_cuts | PASS | 11 shots, mean 2.68 s, longest 5.13 s |
| cuts_inside_recordings | PASS | every cut verified against its recording's length when the build resolved it |
| prompt_to_game_quick_cuts | PASS | 3 gameplay moments in the build beat |

## idea

| Check | Result | Detail |
|---|---|---|
| genuine_prompt_excerpt | PASS | MY FIRST PROMPT · EXCERPT: verbatim from the first development prompt (2026-10-15), section 1 PRODUCT OVERVIEW, quoted verbatim with the title line omitted |

## features

| Check | Result | Detail |
|---|---|---|
| labels_are_implemented | PASS | CHARACTERS / 36 PUZZLES · 5 WORLDS / HINTS THAT TEACH — sources in spec.claims |

## iteration

| Check | Result | Detail |
|---|---|---|
| real_before_after | PASS | FIRST PLAYABLE BUILD (04e1734) vs LATEST BUILD (5b6cecb), same level and taps |
| human_direction_stated | PASS | I kept reviewing it, finding problems, and asking Claude to improve things. |

## result

| Check | Result | Detail |
|---|---|---|
| built_with_claude_text | PASS | BUILT WITH CLAUDE. |
| still_in_development | PASS | STILL IN DEVELOPMENT |

## cta

| Check | Result | Detail |
|---|---|---|
| exact_cta_text | PASS | COMMENT ‘LINK’ / OR DM ME ‘LINK’ |
| cta_narration | PASS | Want the prompt? Comment LINK, or DM me LINK. |
| ends_on_active_gameplay | PASS | last shot: hook until the final frame |
| motion_in_last_second | PASS | mean change in the card over the last second: 1.3/255 |
| devmimo_brand_small | PASS | Mimo 170×200 px + @DEVMIMO |
| no_repository_mention | PASS | CTA asks for the prompt only |

## loop

| Check | Result | Detail |
|---|---|---|
| end_flows_into_start | PASS | ends at hook 6.10 s; opens at hook 6.10 s |
| last_vs_first_frame | ADVISORY | mean difference in the card, last vs first frame: 33.9/255 (overlays differ by design) |

## layout

| Check | Result | Detail |
|---|---|---|
| inside_instagram_safe_area | PASS | all regions inside x 60–900, y 250–1520 |
| nothing_in_side_margins_measured | PASS | brightest pixel in the side margins over 59 frames: 25/255 (background ≈ 15–40) |
| subtitles_below_gameplay | PASS | card ends y 1371, subtitles start y 1384 |
| text_over_title_bar_only | PASS | overlays end at y 534 (the recording's title bar + banner) |

## subtitles

| Check | Result | Detail |
|---|---|---|
| dynamic_groups | PASS | 22 groups, ≤5 words each |
| restrained_orange | PASS | 5/74 words highlighted (Claude, Claude., LINK,, LINK., prompt?) |

## privacy

| Check | Result | Detail |
|---|---|---|
| no_repo_or_account_names | PASS | none of the private terms in props, script, caption, prompt, spec |
| game_title_screens_excluded | PASS | no cut starts on a home/title screen; the level titled with the project name is cropped below its title bar |

## honesty

| Check | Result | Detail |
|---|---|---|
| claims_sourced | PASS | 36 puzzles: 36 curated levels in apps/game/data/levels/curated.json at the latest build; 5 worlds: Little Workshop, Candy Factory, Parcel Station, Neon Circuit, Space Logistics (scripts/ui/worlds.gd); characters with personalities: The Crew: Bloop, Zip, Glitch, Mochi, Captain Naps, Dr. Rix (docs character system); reactions recorded in the clips; hints that teach: three-step hints (area, tile, rotation); 'Hint 1 of 3' recorded in fail_fix; built with Claude: every commit after the initial README is co-authored by Claude Code, from the creator's five written briefs; still in development: not published; no device testing; iOS not compiled (known limitations) |
| no_unverified_claims | PASS | no time-to-build, publication or 'Claude did it alone' claims in narration |

## deliverables

| Check | Result | Detail |
|---|---|---|
| all_files | PASS | 9 files + metadata + QA report |
| cover_survives_every_crop | PASS | brightest pixel outside x 180–900, y 430–1490: 35/255 (that box is kept by the 1:1, 4:5, 3:4 grid and 4:5-as-9:16 crops) |
| cover_4x5 | PASS | 1080x1350 |
