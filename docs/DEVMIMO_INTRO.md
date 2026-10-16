# DevMimo intro and logo sting

A 26-second cinematic intro for DevMimo (1080×1920, 30 fps) and a reusable 5-second logo animation. Both are built on the existing V2.2
pieces. Nothing in the pipeline was rebuilt, and no other video format was changed.

```bash
.venv/bin/python examples/devmimo/build_intro.py              # narrate → time → mix → render both → master → QA
.venv/bin/python examples/devmimo/build_intro.py --reuse-voice # keep the cached narration (data/devmimo/)
npx remotion still src/index.tsx MimoSheet out.png             # mascot expression sheet
```

Outputs go to `demos/devmimo/`:

- `devmimo_intro.mp4`
- `devmimo_intro_poster.png`
- `devmimo_intro_contact_sheet.png`
- `devmimo_intro_storyboard.json`
- `devmimo_intro_qa.json`
- `devmimo_logo.mp4`
- `devmimo_logo_contact_sheet.png`

The MP4s are git-ignored, like every other render.

## What was reused

| Piece | Source |
|---|---|
| Narration | `tts.narrate`: Kokoro `am_adam` @ 1.05 via kokoro-onnx; spoken forms for Mimo / DevMimo / MCP |
| Voice tone | `audio_profile.match_eq` (reference EQ, Kokoro strength 0.5), compressor, loudnorm per scene |
| Music | `audio.music_bed(style="warm_pad")`, ducked under speech; level from `audio_profile.bed_gain_db` (reference bed −22 dB under speech) |
| SFX | `audio.whoosh / pop / tick / chime / stamp / plug` plus three new synths in the build script (sub boom, riser, key clicks, glitch) |
| Master | linear gain to −14 LUFS + limiter, re-measured until loudness and true peak (≤ −1 dBTP) both hold |
| QA | `video_validation.technical`, `audio_profile.compare`, plus intro checks in `examples/devmimo/qa.py` |
| Fonts | the bundled Figtree, Instrument Serif and JetBrains Mono (`ensureFonts`) |

## New Remotion code (`src/devmimo/`)

| File | Contents |
|---|---|
| `theme.ts` | colour roles read from `brand/tokens.json` (FIELDNOTES premium: ground, ink, accent), clamped easing helpers, word-frame lookup |
| `Mimo.tsx` | the brand's recurring character (`brand/character/identity.json`, same drawing as `src/premium/Blob.tsx`) with the intro's controls: blinks (auto + scripted), breathing, nub wave, typing bob, squash, sparkles; expressions neutral / happy / surprised / wink / focused; mouth driven by narration loudness |
| `Logo.tsx` | `LogoMark` (the character's face between code brackets), `LogoReveal` (the 150-frame animation, reusable at any scale) and the `DevMimoLogo` composition |
| `Backdrop.tsx` | dot grid drifting under a warm key light, vignette |
| `Scenes.tsx` | hook, reveal, build, topics, no-fluff and outro scenes |
| `DevMimoIntro.tsx` | composition, slab wipe, slow camera push, ambient code glyphs, `DevMimoPoster`, `MimoSheet` |

Compositions: `DevMimoIntro`, `DevMimoLogo`, `DevMimoPoster`, `MimoSheet`.

## Timing

Each scene lasts lead-in + measured speech + tail. The tails share what is left of the 30 s by the storyboard's `hold` weights, so the
picture always waits for the voice. Every animation that lands on a word reads that word's start from `props.scenes[].words`. Sound
cues can be anchored to a word index (`"word": n` in the storyboard's `sfx` list), so the sound and the picture use the same frames.

## Pacing (Instagram pass)

The first cut ran 30.03 s. The pacing pass brought it to 26.0 s:

- **Hook:** pulled forward. "STILL STUCK?" now holds 0.45 s after the word.
- **Reveal:** "Meet Mimo" comes 0.2 s sooner and the reveal lasts 2.4 s instead of 3.6 s.
- **Topics:** faster.
- **No-fluff terminal:** kept readable.
- **End card:** the logo and CTA stay on screen for at least 1.5 s.

Narration runs at Kokoro speed 0.95, which measured 159 wpm while speaking (54 words in 20.36 s of audio). The storyboard holds the
pacing targets (`pacing.target_s`, `wpm_target` 145–165, `end_card_min_s`), and QA checks the speaking rate and the end-card hold.

## Character and colours

Mimo is the repo's recurring character. Its shape and palette come from `brand/character/identity.json`; every colour comes from
`brand/tokens.json`. Change either file and the intro follows.

The on-screen name "Mimo" comes from the DevMimo brief. `identity.json → public_name` is unchanged (`null`), so other formats still
never show a name.

## QA

`devmimo_intro_qa.json` has two parts:

- **Deterministic checks:**
  - technical;
  - timing (each scene ≥ its narration);
  - reference audio;
  - frame-0 contrast;
  - motion share and longest static stretch;
  - palette share;
  - logo technical checks.
- **Visual review** (`examples/devmimo/visual_review.json`): what was seen on extracted frames and what was fixed. It is labelled as
  an inspection, not a computed check.
