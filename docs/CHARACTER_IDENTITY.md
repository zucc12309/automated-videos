# Character identity

The recurring character is what should make five different reels read as one account. Its spec lives in
`brand/character/identity.json`; the renderer (`src/premium/Blob.tsx`) and the visual director
(`video_mcp/creative/visual_director.py`) both read from it, and QA (`video_mcp/quality/premium_checks.py`) checks it.

## Who it is

- **Silhouette.** A soft marshmallow block.
  - Shape: dome top and rounded bottom corners, width:height 1.27.
  - Base band: the lower 36% is a slightly darker band.
  - No limbs at rest. A short rounded nub appears only when it points.
- **Palette.** Body `#f6f6f2`, band `#d9d9d3`, eyes `#121318`, cheeks `#f3b4c2`, sparkle `#ffd76a`.
- **Face.**
  - Eyes: two vertical pill eyes.
  - Cheeks: pink, on the band line.
  - Mouth: shows only while it speaks, driven by the narration's visemes and loudness.
- **Personality.** Curious, clever, slightly playful and technically fluent. Occasionally impressed; never loud or childish.
  It reacts to the content and never performs for its own sake.
- **Name.** The internal working name is `provisional_name` (Mochi). `public_name` stays `null`, and `brand_profile.public_character_name`
  in `config.json` stays `null` until you approve a name. No component renders the provisional name; a test enforces this, and the QA
  check `no_unapproved_name` fails if it shows up in on-screen text.

The design was reconstructed from frames of Reference A and then checked against them on a still sheet
(`npx remotion still src/index.tsx BlobSheet`). It is a close match, not a pixel copy of the Mac renderer's asset. See
`reports/V22_VISUAL_GAP_AUDIT.md`.

## States

`idle, speaking, thinking, pointing, typing, explaining, surprised, celebrating, warning, confused, presenting, exiting`

| State | What it looks like | Used when |
|---|---|---|
| speaking | mouth follows the visemes, small nods on stressed words | explanation beats |
| thinking | eyes look up, "…" glyph | before/after comparisons |
| pointing | leans and extends the nub toward the target | the CTA keyword |
| typing | eyes down, quick bobbing | code and terminal beats |
| explaining | nub toward the diagram | workflow and architecture diagrams |
| presenting | leans toward the object | a repository card |
| surprised | wide eyes, "!" glyph, hop | the reveal signature, at most once |
| celebrating | arc eyes, sparkles, hop | a storyboard-requested win, at most once |
| warning | micro-shiver, "!" glyph | caution and mistake beats |
| confused | tilt, "?" glyph | the "weak prompt" beat |
| exiting | sinks below the hairline | end of video |

## Scales and placement

| Scale | Size (px at 1080 wide) | Rule |
|---|---|---|
| closeup | 520 | the opening acknowledgement only (and the loop return) |
| medium | 260 | beside a single object it introduces; the CTA |
| companion | 150 | dense demonstrations (code, terminals, diagrams), dimmed 10–15% |
| hidden | 0 | full-frame footage only |

The anchor is `home` (lower left), `right` (the CTA) or `centre` (the hook). The character springs between scales and anchors, so it
never jumps.

## Signatures

1. **Entrance.** On the hook it pops up from below the hairline: one blink and a tiny nod.
2. **Reveal.** Once per video, on the most impressive item, it double-blinks and goes to surprised eyes with a hop.
   "Most impressive" means the most GitHub stars, otherwise the first stat or prompt "after".
   If the storyboard asks for its own big reaction (surprised or celebrating), that replaces the automatic one.
3. **CTA.** It leans toward the keyword, points with the nub and winks.

## Who decides

The visual director stages every beat and writes the reason into the job's `props.json` under `beats[].direction.character`.
A storyboard can request a state per scene with `character_action`; requests are honoured on the scene's first beat.
`production.character` (`on` / `off` / `auto`) and the storyboard's `creative_direction.character` switch it off entirely.

## QA

These checks run on every premium render. They are deterministic and read `props.json`:

- `character_staged`
- `character_scales`
- `signature_entrance`
- `signature_cta`
- `one_reveal_reaction`
- `character_present` (hidden only on footage)
- `no_unapproved_name`
