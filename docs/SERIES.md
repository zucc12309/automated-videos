# Series system: Mimo Found This on GitHub

A recurring Reels/Shorts series. Each episode features one GitHub repository and a verified demonstration of it. Episodes are built
from a short spec; numbering, layout, covers, narration, subtitles, sound, QA and metadata come from the series system. Nothing in
the shared components is specific to one episode.

```bash
.venv/bin/python examples/series/build_episode.py series/mimo-found-this-on-github/specs/<repo>.json --validate-only
.venv/bin/python examples/series/build_episode.py series/mimo-found-this-on-github/specs/<repo>.json
.venv/bin/python examples/series/build_episode.py SPEC --episode 12    # manual number; refused if another repository holds it
```

## Status

- **The series system is built and tested end to end** on a labelled pipeline-test fixture
  (`tests/fixtures/series/pipeline_test_spec.json`). That fixture used a temporary registry and was rendered outside `outputs/`, so it
  never took a real number. It passed all 52 deterministic checks, and its frames were inspected.
- **EP. 001 has not been produced.** The briefed repository, `fikriaf/HandCam-Control`, was verified and rejected, and the producer
  chose a different repository. See `series/mimo-found-this-on-github/candidates/rejected.json`:
  - Hand tracking and gesture recognition are real. Its own detector code was run on scripted landmarks.
  - It never moves the operating-system cursor or clicks. Actions stay inside its own page, and pinch and OK are TODO stubs.
- No episode number is allocated yet. The first spec that is built becomes EP. 001.

## Layout

| Path | What |
|---|---|
| `series/<slug>/series.json` | name, header, tagline, footer, handle, palette (charcoal `#0E0F12`, ivory `#F5F0E8`, orange `#ECA044`), pacing (22–28 s, 145–165 wpm, 2 s outro), banned phrases, safe zones |
| `series/<slug>/specs/*.json` | one authored spec per episode |
| `series/<slug>/episodes/episode-NNN.json` | the registry: one record per allocated number |
| `series/<slug>/candidates/rejected.json` | repositories checked and not produced (never numbered) |
| `video_mcp/series.py` | registry, numbering, spec validation, subtitle grouping, caption and script writers |
| `examples/series/build_episode.py` | the builder (narration → timing → subtitles → sound → render → covers → QA → metadata) |
| `examples/series/qa_episode.py` | episode QA |
| `src/series/` | `theme.ts`, `layout.json` (shared with QA), `Cover.tsx`, `Episode.tsx`, `Visuals.tsx` |

## Numbering

- The next number is the highest in the registry plus one. The registry covers reserved, draft, rendered and published episodes.
- A repository that already has a record keeps its number, so re-rendering never allocates a new one.
- Overrides (`--episode N`) are accepted only if that number is free or already belongs to the same repository.
- Records are created with `O_EXCL`, and an existing record is never overwritten.
- Record number and repository never change. Status only moves forward: reserved → draft → rendered → published.
- Labels are three-digit: `EP. 001`, `EP. 010`, `EP. 100`.

## What a spec needs

- `repository`, `title` and `cover_headline` (lines).
- `repo_card.description` and an optional `mascot_expression`.
- `verified_features`. Each entry has an id, label, claim, `status` (`verified-run` or `verified-source`) and `evidence` (a file and
  line, a test or a capture).
- `demo.status`:
  - `captured`;
  - `run-in-sandbox`;
  - `source-reenactment` (gets the on-screen tag "RE-ENACTED FROM SOURCE");
  - `fixture`.
- Demo panels for the hook, the split demo and the payoff. Panel kinds:
  - `hand`: a keyed path with the 21-landmark MediaPipe topology;
  - `cursor`;
  - `terminal`;
  - `code`;
  - `image`: a real screenshot in `public/`.
- `flow` nodes.
- Optional narration. The discovery and payoff lines default to the series templates, and the hook defaults to the title.

Validation blocks a render when:

- an on-screen label or flow node cites an unverified feature;
- the copy uses a banned hype phrase;
- the copy quotes repository statistics such as stars, forks or downloads.

## Episode structure

| Scene | Content |
|---|---|
| Hook | Demo stage (desktop + webcam picture-in-picture, or one panel) and the headline slammed line by line on narration words. No logo intro. |
| Discovery | Series header + EP badge. Repo card slides in. Mimo pops up from a hairline, surprised, then points. |
| Demo | Split panels joined by an orange animated wire. Label chips land in order on narration words. Mimo is curious and tilts with cursor speed. |
| Flow | The repository name, then three nodes that light in turn. Mimo walks alongside, thinking. |
| Payoff | The demo replays. Mimo is excited. "WOULD YOU TRY THIS?" and a stamp "EP. NNN — SAVED TO MIMO'S FINDS" on "Follow". |
| Outro (2 s) | Mimo, the DevMimo wordmark, the EP badge, and "FOLLOW @devmimo · EP. NNN+1 SOON". |

Every scene has a slow camera push. Subtitles and a small series bug ("EP. NNN · MIMO FOUND THIS ON GITHUB") sit outside it.

**Subtitles**

- Burned in, 3–5 words per phrase.
- Phrases break at punctuation and pauses, never across a sentence end.
- Emphasis terms are shown in orange.
- One band at y = 1420, inside the safe zone and clear of every demo block.

## Narration and sound

- Kokoro `am_adam`. The builder measures the speaking rate and re-narrates at an adjusted Kokoro speed until it lands in 145–165 wpm,
  interpolating between attempts. Audio is never time-stretched.
- Word timings are `energy_snapped`: sentence boundaries are exact, and words inside a sentence are estimated and snapped to energy
  minima.
- SFX cues use the same frame formulas as the components:
  - click and bass accent at frame 0;
  - headline pops;
  - press ticks wherever a path pinches;
  - label and node ticks;
  - stamp on "Follow".
- Two exports are made: the final (with the ducked warm-pad bed) and a no-music version for native Instagram audio.
- Both are mastered to −14 LUFS with a 4× oversampled true-peak limiter (≤ −1 dBTP).

## Covers

`SeriesCover` is a designed composition, not a video frame. All essential elements sit inside the square safe region (x 60–1020,
y 420–1500):

- header;
- EP badge;
- headline (the largest type, auto-fitted);
- project illustration;
- Mimo;
- footer.

The 4:5 (1080×1350) and 1:1 (1080×1080) previews are centre crops of the 1080×1920 master. QA renders a mask of the essential
elements and fails if any pixel lies outside the square. It also writes `qa/cover-grid-thumbnail.png`, which shows the cover at real
profile-grid size.

## Outputs

`outputs/<slug>/episode-NNN/` holds:

- `-final.mp4`
- `-no-music.mp4`
- `-cover.png`
- `-cover-4x5.png`
- `-cover-square.png`
- `-script.md`
- `-caption.md`
- `-metadata.json`
- `-qa-report.md`
- `qa/`, holding the contact sheet, cover mask, guides, grid thumbnail and `visual_review.json` when inspected.

MP4s are git-ignored, like every render.

The metadata records:

- verified features and evidence;
- demonstration status;
- source references;
- narration and word count;
- speaking rate and the voice-speed search;
- duration;
- caption and hashtags;
- loudness;
- QA summary;
- output paths.

It never records stars, forks, downloads or contributor counts.

## QA

The deterministic checks cover both exports:

- technical, plus the H.264/AAC codecs;
- loudness and true peak for each export;
- duration (22–28 s) and speaking rate;
- each scene fits its narration;
- subtitles: transcript match, group size, readable time, no time overlap, sync, safe zone, clear of demo blocks;
- layout blocks inside the safe zone;
- frame-0 contrast;
- motion share and the longest static stretch;
- palette share;
- cover: sizes, crop safety, side margins, EP legibility at thumbnail size, headline is the largest type;
- mascot single source;
- copy claims.

The visual review is recorded separately and labelled as an inspection.

## Mascot

`MimoMascot` wraps the existing `src/devmimo/Mimo.tsx` (`brand/character/identity.json`), which is not redrawn or regenerated. The
series states are curious, surprised, thinking, excited and pointing. They use three props added to Mimo:

- `tilt`;
- `point` / `pointAngle` (the identity's "point" gesture);
- `hop`.

All three default to 0, so the DevMimo intro renders as before.
