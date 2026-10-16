# Brand package

Everything that makes every reel look like the same publication and the same character.

| File | Purpose |
|---|---|
| `tokens.json` | `fieldnotes-premium` design tokens (colour, type, spacing, radius, shadow, motion, frame, caption, character scale). Read by Remotion (`src/premium`) and Python QA |
| `character/identity.json` | Versioned character spec: silhouette, palette, face, visemes, states, gestures, scales, placement rules, personality, signatures. Public name is configurable (null = never shown) |
| `voice.json` | Narration voice profile (Kokoro `am_adam`, speed 1.05) and mastering targets |
| `audio_profile.json` | Reference A's measured sound (loudness, bed level/warmth, pitch, pauses, voice spectrum) and the render targets derived from it; used by narration, music, mastering and audio QA |
| `motion.json` | Motion signature, transition vocabulary and rhythm rules |
| `series.json` | Wordmark/lockup and internal series labels with their default CTA keyword |
| `cta_templates.json` | CTA keywords, secondary lines, truthful narration, and the DM-delivery switch (off) |
| `reference/` | Reference A measurements and frame strip used by the reference-style QA |

Change the brand here, not in components.
