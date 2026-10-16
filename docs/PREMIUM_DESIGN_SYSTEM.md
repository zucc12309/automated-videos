# FIELDNOTES premium design system (`fieldnotes-premium`)

This is the V2.2 production default. It keeps Reference A's editorial look (dark publication frame, one object at a time, blur
transitions, the character) and adds the V2 machinery (semantic layouts, a visual director, QA).

| Source of truth | Path |
|---|---|
| Tokens | `brand/tokens.json` |
| Motion vocabulary | `brand/motion.json` |
| Renderer | `src/premium/` (`tokens.ts`, `Frame.tsx`, `Objects.tsx`, `Blob.tsx`, `PremiumVideo.tsx`) |

How it is selected:

- **Default.** `production.style = "premium"` with `production.theme = "fieldnotes-premium"`.
- **Studio renderer.** Set `production.style = "studio"` (or any other theme) to get the V2 studio renderer, unchanged.

## Palette

| Token | Hex | Use |
|---|---|---|
| ground | `#0a0b0f` | background (radial lift `#111219`, grain 6%, vignette) |
| surface / surfaceRaised | `#17171e` / `#1f2028` | cards, rows |
| line | `#2a2b34` | hairlines, card dividers |
| ink / inkSoft | `#efefea` / `#c9c9c4` | primary / secondary text |
| muted / dim | `#9b9ca5` / `#62646e` | already-spoken headline words / masthead |
| accent | `#8ea2ff` | selection box, packets, progress hairline |
| success / danger / warn | `#7ed39a` / `#f08a8a` / `#f2b25c` | toggles and diff additions / removals / caution label |
| keyPink, avatar | `#f39ab1`, `#e07a4f` | code keys, repository avatar tiles |

Measured on the reference: ground `rgb(11,13,16)`. The QA ground check allows a maximum channel difference of 18.

## Type

All three fonts are open-licensed (SIL OFL) and bundled in `public/fonts/` with their LICENSE files. They are loaded with
`@remotion/fonts`, so renders never depend on system fonts.

- **Figtree:** UI and headings.
- **Instrument Serif italic:** the editorial emphasis inside the selection box.
- **JetBrains Mono:** code, terminal, masthead.

Mobile type scale (px at 1080 × 1920):

| Role | Spec | Implemented |
|---|---|---|
| Hook | 80–120 | 104 (longer than 34 characters) / 118 |
| Headings | 64–88 | repository name 64, warning 76, browser title 64 |
| Body | 40–56 | 40–50 (lists 44, diagram nodes 44, terminal 40, README 46) |
| Kinetic headline (caption role) | 48–64 | 60 |
| Meta | 32–40 | 32 (masthead, card meta, badges, chips) |
| Code | not in the spec | 30–40, sized to the longest line (at most 48 characters); documented exception |

QA mirrors these numbers in `premium_checks.PREMIUM_TEXT`. `tests/test_v22.py` fails if any literal font size in
`src/premium/Objects.tsx` drops below 32 px, or if a table entry falls under its role's minimum.

## Frame

The publication frame has five parts:

- **Masthead.** `FIELDNOTES · SERIES` on the left and `NN / NN` on the right, in mono, letter-spaced 6.
- **Kinetic headline.** The spoken words, paged two lines at a time.
  - Placement: top band, y 300.
  - Reveal: each word resolves from blur as it is spoken; earlier words fall back to muted.
  - Emphasis: the emphasis word gets a serif-italic selection box with corner handles.
- **Stage.** One centred object, 840 × 760, starting at y 520.
- **Character.** Home position lower left; see `docs/CHARACTER_IDENTITY.md`.
- **Progress hairline.** At y 1690.

## Semantic motion primitives

Each storyboard intent maps to a layout (`video_mcp/creative/semantic_router.py`). Each layout maps to one premium object. The router
records *why* in `beats[].layoutReason`, and the visual director records the transition and character reasons in
`beats[].direction`.

| Primitive (brief) | Component | Router layouts |
|---|---|---|
| EditorialReveal | `EmphasisTile`, `PullQuote` | heroWord, quote, docStamp |
| CodeMorph / GitDiffReveal | `CodeEditor` (diff only when `code_language == "diff"` or both `+ ` and `- ` lines exist) | codeBlock |
| TerminalExecution | `TerminalRun` | terminal |
| RepositoryReveal | `RepositoryReveal`, `StatFigure` | repoCard, starMeter |
| WorkflowConnection | `Workflow` (flow / hub with travelling packets) | flowDiagram, nodeGraph, repoConnect |
| BrowserInteraction | `BrowserWindow`, `PhoneNotice` | browserMock, deviceMock, chat |
| BeforeAfterTransform | `BeforeAfter` (`prompt_before` → `prompt_after` morph) | splitCompare, compare |
| FocusHighlight | headline selection box + `ReadmePanel` key-line highlight | readmeScroll |
| CharacterReaction | `Blob` states, staged by the visual director | every beat |
| CameraFocus | per-beat camera push (2.5%), "focus" transition (6%) | continuity rule |
| EditorialTransition | blurDissolve / expand / focus / push / cut | `brand/motion.json` |
| SignatureCTA | `SignatureCTA` (recap toggles, then Comment “KEYWORD”) | outroCTA |
| (hook) | `PremiumHook`: readable on frame 0, brand/series lockup, item avatars | hookBold, hookStack |

## Transitions and rhythm

The visual director (`video_mcp/creative/visual_director.py`) picks a transition by continuity:

| Transition | When |
|---|---|
| cut | first frame only |
| expand | a repository card grows into its own demonstration |
| focus | a detail inside the same scene |
| push | the next numbered item |
| blurDissolve | unrelated objects |

Rhythm rules:

- Every supporting beat holds at least 1.6 s; shorter beats are merged into the previous one.
- About 5 visual changes per 10 s at most.

Reference A measures 3.25 visual changes per 10 s (`brand/reference/reference_a_stats.json`).

## Reference-style QA

`video_mcp/quality/reference_compare.py` measures each premium render against Reference A and writes the results to
`qa/reference_compare.json`. It produces:

- ground colour, mean luminance, and change rate (frame differences at 4 fps);
- `qa/reference_side_by_side.jpg`, the reference strip over the render strip.

These are pixel statistics only. Whether the render *feels* like Reference A needs a person to look at the side-by-side sheet.
