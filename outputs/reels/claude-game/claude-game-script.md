# I built this game with Claude · narration script

29.5 s · 74 words · 168 wpm while speaking (Kokoro, measured) · 1080×1920 · 30 fps

| Time | Beat | Narration | On screen | Footage (real gameplay) |
|---|---|---|---|---|
| 0.0–4.7 s | hook | Making games used to feel impossible without a whole development team. | I BUILT THIS GAME / WITH CLAUDE. | hook @ 6.10s |
| 4.7–7.5 s | idea | But I wanted to see what I could build with Claude. | MY FIRST PROMPT · EXCERPT: “Players rotate conveyor belt tiles to guide packages from sources to matching destinations. … The game should feel: Immediately understandable · Visually satisfying · Extremely responsive” | first @ 1.78s |
| 7.5–11.6 s | build | So I gave it my game idea, and started making it playable. | — | solve @ 1.90s, neon @ 4.20s, big @ 4.60s |
| 11.6–18.0 s | features | Characters with personalities. Thirty-six puzzles, five worlds, and hints that teach. | CHARACTERS<br>36 PUZZLES · 5 WORLDS<br>HINTS THAT TEACH | menus @ 3.75s, menus @ 8.60s, fail_fix @ 5.00s |
| 18.0–23.2 s | iteration | I kept reviewing it, finding problems, and asking Claude to improve things. | FIRST PLAYABLE BUILD vs LATEST BUILD (same level · same taps · two real builds) | c06-old | c06-new @ 4.10s |
| 23.2–25.8 s | result | And this is what I ended up building. | BUILT WITH CLAUDE.<br>STILL IN DEVELOPMENT | big @ 5.50s |
| 25.8–29.5 s | cta | Want the prompt? Comment LINK, or DM me LINK. | COMMENT ‘LINK’<br>OR DM ME ‘LINK’<br>@DEVMIMO | hook @ 2.33s |

## Clips

- **hook**: Level 33 (Space Logistics): last taps, Run, delivery, crew celebration
- **first**: Level 1 with the onboarding coach
- **solve**: Level 20 (Parcel Station) from a fresh board
- **neon**: Level 26 (Neon Circuit) crossing
- **big**: Level 36: final taps, Run, celebration (title bar cropped)
- **menus**: The Crew collection, character detail, Levels
- **fail_fix**: Level 8: early Run fails with an explanation, hint, fix, deliver
- **c06-new**: Level 6, latest build
- **c06-old**: Level 6, first playable build (same taps, same timing)

## Claims and where they come from

- **36 puzzles**: 36 curated levels in apps/game/data/levels/curated.json at the latest build
- **5 worlds**: Little Workshop, Candy Factory, Parcel Station, Neon Circuit, Space Logistics (scripts/ui/worlds.gd)
- **characters with personalities**: The Crew: Bloop, Zip, Glitch, Mochi, Captain Naps, Dr. Rix (docs character system); reactions recorded in the clips
- **hints that teach**: three-step hints (area, tile, rotation); 'Hint 1 of 3' recorded in fail_fix
- **built with Claude**: every commit after the initial README is co-authored by Claude Code, from the creator's five written briefs
- **still in development**: not published; no device testing; iOS not compiled (known limitations)
