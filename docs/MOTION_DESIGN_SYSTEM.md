# Motion design system

## Principles

Motion explains or emphasises; nothing moves without a job. One theme per video. Text stays in the cross-platform safe
area (x 120–960, y 290–1248); the stage is 840 × 700 at (120, 360); captions grow upward from the safe-area bottom.
Body text ≥ 30 px, labels ≥ 22 px at 1080 px width. Animation is frame-based (`useCurrentFrame`, `interpolate`,
`spring`); no `Date`, `Math.random`, CSS transitions or timers, so renders are deterministic.

## Tokens

* `src/studio/themes.json` — 8 themes shared by Remotion and the Python QA: **carbon, midnight, warm-editorial,
  minimal-white, tech-mono, soft-gradient, product-launch, cinematic-dark**. Each defines bg, bg2, surface, ink,
  muted, line, accent, accent2, highlight, dark flag, background treatment and type family. All pass WCAG checks
  (ink and muted ≥ 4.5:1 on bg, accent ≥ 3:1, ink on surface ≥ 4.5:1) — enforced by a test.
* `src/studio/tokens.ts` — fonts, safe area, stage, the V1 palettes (kept), temperaments, punch.
* `src/studio/motion.tsx` — easing (`EASE.standard/enter/exit/inOut`), durations (`DURATION.micro…draw`), springs
  (`SPRING.gentle/snappy/overshoot`).

## Grammar (`motion.tsx`)

| Group | Behaviours | API |
|---|---|---|
| ENTER | fade, slide, scale, mask, reveal | `enterStyle(kind, frame, {delay, duration, amplitude, direction, easing})` |
| EMPHASIZE | pulse, zoom, highlight, underline, counter | `emphasisScale`, `WordEmphasis`, `Counter` |
| CONNECT | line_draw, node_link, flow, morph | `DrawPath`, `FlowDot` |
| EXIT | fade, push, mask, collapse, cut | `exitStyle(kind, frame, end, params)` |
| Camera | static, subtle_push, dolly, pan_left/right, parallax | `cameraStyle`, `Parallax`; storyboard `motion.camera` drives the per-beat push |

Primitives: `MaskedText`, `CharReveal`, `WordEmphasis`, `Counter`, `DrawPath`, `FlowDot`, `CardStack`, `Parallax`,
`typed()` (code typing with caret).

## Layouts

17 V1 layouts kept (heroWord, bigNumber, quote, mascotCloseup, listStack, steps, compare, repoCard, terminal, chips,
starMeter, deviceMock, chat, nodeGraph, hookStack, docStamp, recap) plus V2 (`LayoutsV2.tsx`):

| Layout | Shows | Data (storyboard `visual`) |
|---|---|---|
| codeBlock | syntax-highlighted code typing in an editor window; font shrinks to fit (≥ 24 px) | `code`, `code_language` |
| flowDiagram | request → response chain, connectors draw, packets travel | `nodes` (or points) |
| timeline | rail draws, dated events land | `timeline` (`"2025: event"`) or `steps` |
| chartBars | bar series, last bar counts up | `series_labels`, `series_values` (source numbers only) |
| browserMock | browser window, address bar, UI rows, cursor click | points, `url` |
| warningCard | caution label, drawn rule, underlined emphasis | heading, label, points |
| splitCompare | titled two-column comparison, rows aligned | `compare_titles`, `compare_left`, `compare_right` |
| cinematic | full-bleed footage graded to the theme, heading composited | scene asset |
| statRing (generated) | ring fills to a percentage stat | stat |

## V2.1 retention changes (from review of a generated reel)

| Note | Change |
|---|---|
| Stronger first two seconds | `hookBold`: the hook statement in 104–124 px type, fully visible on frame 0 and mid-"slam"; count in the accent colour, drawn underline, item avatars fly in. Default for every hook. Prompts and the template writer now require a bold statement that starts with the count/payoff (no soft intros, no multipliers absent from the data). In HYBRID, an establishing shot plays *behind* the bold type. |
| More visual movement | `readmeScroll` (the real README scrolls through a reading band, focus line highlighted), `repoConnect` (repo hub with links drawing and packets flowing to its topics/points), repo cards float and their topics run as a marquee. Supporting beats inside repo items keep repo visuals; scene openers are never reused as filler. |
| Larger text | Minimum body text raised to 36 px (labels 26 px) and enforced by QA; repo descriptions 46 px, chips 46, device rows 38, flow nodes 46, split columns 42, code 28–40 px auto-fit. A test fails if any layout's declared size drops below the minimum. |
| More memorable ending | `outroCTA`: items tick off fast, then one big imperative call to action (heading ≤ 26 chars) with a pulsing save icon and "watch it again" loop arrow; the final beat loops to the hook. |
| Imported motion graphics | `motionClip` + `import_motion_clip` tool: a clip exported from Claude's motion/design tools (or any editor) is validated, stored in `data/motion_library/`, and placed in a scene with `assets: [{"kind": "graphic", "path": "library:<id>"}]`. |

## Semantic selection (`video_mcp/creative/semantic_router.py`)

Intent per scene (from the director, or inferred from narration and data). Score =
4.0·relevance + 0.8·narrative fit + 1.0·readability − 1.5·recent use − 0.6·same motion family thrice − 0.4·cost
− 0.3·complexity on short beats + 0.2·theme fit. Missing data excludes a layout (no bigNumber without a number, no
hookStack/recap without numbered items, no repoCard without API data, no cinematic without footage). Ties break on
sha256(seed, beat, layout) — same storyboard + seed ⇒ same plan. Each choice records its score parts in
`props.json → beats[].layoutReason`.

Timing is speech-driven: beats split at punctuation within pace windows (emphasis 1.0–2.4 s, medium 1.3–3.0 s,
demonstration 2.4–5.5 s, montage 0.9–1.8 s). Diagrams, devices, data, footage and split comparisons **hold** for the
whole line instead of being cut into filler beats. Structural V1 rules remain (repo card opens a repo item, recap opens
the outro, final beat loops to the opening frame, no back-to-back repeats).

## Presenter

The character appears only where the storyboard motivates it (`scene.character`, default hook and outro in `auto`),
enters/leaves with a spring, and is never centred over content except in `mascotCloseup`. `production.character: "off"`
removes it. V1 props (no `character` field) keep the always-on presenter.

## New components (component forge)

`video_mcp/creative/component_forge.py`: allow-listed imports only; forbidden: eval/Function/require/dynamic import,
network, storage, timers, randomness, process/window/document, raw HTML, URLs → `tsc --noEmit` → sandboxed
`remotion still` with credentials stripped from the environment → non-blank screenshot → `pending_review` →
explicit `promote(name, reviewer)` adds it to `src/studio/generated/index.ts` and the router catalogue. Example:
`examples/components/StatRing.tsx` (promoted after review in this delivery). Unattended jobs only use approved components.
