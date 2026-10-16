# Game reel: real gameplay + narration

A creator reel built around **real screen recordings** of a game, not mock-ups. First use: `reels/claude-game` ("I built this game with Claude").

| Piece | File |
|---|---|
| Reel spec (beats, narration, cuts, overlays, claims and their sources) | `reels/claude-game/reel.json` |
| Caption / the prompt followers get when they comment or DM "LINK" | `reels/claude-game/caption.md`, `reels/claude-game/prompt.md` |
| Recording driver (Godot autoload) | `examples/game_reel/capture_gameplay.gd` |
| Builder: narration, timing, game-audio mix, render, cover, previews | `examples/game_reel/build_game_reel.py` |
| QA (measured) | `examples/game_reel/qa_game_reel.py` |
| Composition + layout | `src/gamereel/GameReel.tsx`, `src/gamereel/layout.json` (`GameReel`, `GameReelCover`) |

## 1. Record

The game's own engine records the footage: Godot 4.5.1's Movie Maker mode (`--write-movie … --fixed-fps 30`) at 1080×1920 under Xvfb (Mesa llvmpipe).
Time advances exactly 1/30 s per frame, so the clips are deterministic. The driver plays through the game's real input handlers (board taps, button
signals) and draws a translucent touch indicator where each tap lands. The game's own audio (taps, belts, deliveries, celebration) is recorded too.

For the before/after, the same driver plays the same level with the same taps on an **earlier commit** of the game (its first playable build).
That build has no crew system, so it uses a reduced copy of the driver: no unlock calls, and the analytics question is pre-answered as a level-6 player would have done.

Convert each `NAME.avi` to `public/game-reel/NAME.mp4` (H.264, CRF 14) and `data/game-reel/clips/NAME.wav` (24 kHz mono). Both locations are git-ignored.

## 2. Build

```bash
.venv/bin/python examples/game_reel/build_game_reel.py reels/claude-game/reel.json [--reuse-voice] [--skip-render] [--qa-only]
```

- Narration: Kokoro, with the speed searched until the narration measures 150–175 wpm while speaking (the series voice chain).
- Every cut, label and overlay resolves to frames on the narration's word clock. A cut that would run past the end of its recording stops the build.
- Audio: voice, then the game's own sound under each cut (peaks 12 dB below the voice, ducked under speech), then the music bed (left out of the no-music version). Mastered to −14 LUFS and ≤ −1 dBTP.
- Layout: the gameplay card, text overlays (only over the recording's title bar), subtitles below the card, Mimo and the handle all sit inside the Instagram safe area (x 60–900, y 250–1520).
- Outputs go to `outputs/reels/<id>/`: final, no-music, cover (1080×1920, 4:5, square), script, caption, prompt, metadata, QA report, and `qa/` (contact sheet, simulated Instagram UI previews, cover mask, grid thumbnail).

## Privacy

The finished reel must not name the game's repository, account, branches or internal docs. The terms are listed in `data/game-reel/private_terms.json`, which is git-ignored so the names never enter this repository. QA searches every text deliverable and the render props for them.
Footage cuts avoid the home and title screens; the level whose title is the project's name is cropped below its title bar.
