# V2.2 Visual Gap Audit

Date 2026-10-16 · branch `claude/hybrid-video-v2` @ `da6e9ce` · baseline tests: 99 passed, 1 skipped; `tsc` clean.

## Inputs actually inspected

| Input | How |
|---|---|
| Reference A `UnFEATh8FkvrJt6rB5jhqA.mp4` (uploaded twice; identical sha256 `3de121fe…`) | 40.0 s, 1080×1920, H.264 + AAC 48 kHz stereo, metadata "Made with Remotion 4.0.357". Sampled 1 fps contact sheet and full frames at 0.0, 0.6, 2.5, 4.0, 6.6, 9.5, 12, 16.5, 21, 26, 33.5, 38.5 s; repo cards cropped at 7.6/13.6/20.4/28.4 s; audio pitch-tracked |
| Reference B `demo_d_claude_code_repos_v21.mp4` | Rendered in this session (`data/jobs/3c5f0c05aad4`); frames inspected at 0, 1.5, 12.6, 15.5, 20.5, 32.6–35.9 s |
| Source | `src/studio/*`, `src/Character.tsx`, `src/styles/Fieldnotes.tsx`, `src/index.tsx`, `video_mcp/creative/*`, `video_mcp/orchestration/*`, `video_mcp/quality/*`, both V2 reports |

## Rendering paths

* **Reference A was not produced by any code in this repository.** `git ls-remote` shows only `main` (`20348eb`) and this
  branch. The repo's `fieldnotes` style (`src/styles/Fieldnotes.tsx`) is a different, older layout (paper cards); nothing
  here draws the blob character, the "FIELDNOTES / PRODUCT NOTES" lockup, the 9:41 phone notification, the hashed
  key/value panel, the selection-box serif emphasis, or the toggle recap. These exist only on your Mac.
* V2 / V2.1 output (Reference B) comes from `style: "studio"` → `src/studio/StudioVideo.tsx` with `LayoutsText/Data/Story/V2/Retention.tsx`
  and the V1 "Dev" character in `src/Character.tsx`.

### Files to import from the Mac (exact steps)

```sh
cd /Users/priyanshupatel/Downloads/VIDEOS/local-video-mcp
git status --short src video_mcp            # the renderer changes that produced Reference A
git checkout -b fieldnotes-local && git add src video_mcp public config.json && git commit -m "Local FIELDNOTES renderer"
git push -u origin fieldnotes-local          # then ask Claude to diff it against claude/hybrid-video-v2
```
Until then V2.2 **rebuilds the look from the video** (component-by-component list below). Differences that cannot be
known from pixels — exact font files, spring constants, the character's full state set — are listed as "reconstructed".

## What makes Reference A visually superior

1. **One restrained palette**: near-black `#0e0f12`-ish ground with a soft centre lift; ivory/white type; grey for
   secondary words; colour only in tiny accents (green REPO badge / toggles / Done button, blue selection handles and
   progress hairline, one warm avatar tile per repo). Reference B uses saturated theme accents and multicoloured avatar tiles.
2. **Editorial type mix**: sans (Avenir-like) for running copy, italic serif (Baskerville/Caslon-like) for the one word
   that matters and for repo descriptions, small letter-spaced mono for metadata (`FIELDNOTES`, `01 / 06`,
   `GITHUB STARS`, `github.com/owner`). B is almost all heavy sans.
3. **A persistent publication frame**: mono masthead top-left, `NN / 06` counter top-right, hairline progress at the
   bottom. It makes every frame feel like the same publication. B has a chunky progress bar only.
4. **Kinetic headline at the top** instead of bottom captions: words resolve from blur in reading order; spoken words
   white, unspoken grey; the key word swaps to italic serif inside a thin "selection box" with handles. Content sits
   alone in the middle; the bottom third is calm. B stacks captions under the content.
5. **One object per scene, centred, with depth**: a single dark card (≈ 24 px radius, 1 px border, soft shadow) — repo
   card, key/value panel, phone notification, toggle list. B often shows dense multi-element layouts.
6. **Soft, slow transitions**: content blurs and dims out, the next object resolves from blur; no whips, no bounces.
7. **A tiny, recognisable character**: a white marshmallow-shaped blob with two oval eyes and pink cheeks, bottom-left,
   breathing and blinking, dimming when content takes focus. Instantly brandable. B's "Dev" character is large, busy,
   and colour-shifting per video.
8. **Real-world UI metaphors** (lock-screen notification "CLAUDE CODE · now", settings panel with hashes, iOS toggles)
   that read instantly on a phone.

## Where Reference A is weaker (do not copy)

* **First two seconds**: frame 0 shows only the small lockup; the hook copy arrives word by word and the title is
  ~40 px italic. The user's own review asked for a stronger opening.
* **Small type**: headline ~56 px at 1080 width; card copy 28–34 px; mono labels ~20 px. Below the brief's mobile targets.
* **Ending**: toggle recap + "Save this for your next build." — no contextual CTA.
* **Character** never acts on the content (no pointing, reactions or signature gesture).

## Preserve / replace / merge

| Area | Decision |
|---|---|
| Pipeline, providers, budget, approvals, cache, journal, checkpoints, MCP tools, semantic router, QA, repair | **Preserve** (V2) |
| Palette, typography system, frame (masthead, counter, hairline), card treatment, blur transitions | **Replace** V2 studio look with `fieldnotes-premium` (new default theme + new `premium` renderer). Old themes/styles stay selectable |
| Kinetic top headline with serif selection-box emphasis | **Rebuild from A**, sized up to 56–64 px |
| Repo card, key/value panel, phone notification, toggle recap, emphasis tile | **Rebuild from A**, larger type |
| Blob character | **Rebuild from A's silhouette** + identity spec, states, signature behaviours (new) |
| Code typing, flow/node diagrams, README scroll, split compare, CTA, footage compositing | **Merge**: V2 behaviours re-skinned in the A design language |
| Hook | **Replace** A's slow opener with a frame-0 bold hook in A's typography + character acknowledgement |
| Ending | **Replace** with contextual CTA engine (keyword + truthful fulfilment + resources) |

## Implementation priorities

1. `fieldnotes-premium` tokens in `brand/` + bundled OFL fonts (Figtree ≈ Avenir Next, Instrument Serif italic ≈ the
   reference serif, JetBrains Mono ≈ SF Mono) — *reconstructed*, not the Mac's exact files.
2. `premium` renderer: frame, kinetic headline, centred object components, blur transitions.
3. Character identity engine (spec, states, scales, placement, signatures, lip/viseme cue).
4. Hook candidates + bold frame-0 opener; contextual CTA + resource files.
5. Visual director (continuity, rhythm, character staging, transition reasons).
6. `vibe_coding` format; reference-driven QA; demos; docs.

## Voice

Reference A's narration pitch-tracks at a median F0 ≈ 121 Hz (p10–p90 91–212 Hz): a male voice, consistent with
`config.json → voice: "am_adam"` (Kokoro, `voice_speed` 1.05). The voice profile pins it. Kokoro weights cannot be
downloaded in this container (Hugging Face blocked); a third-party npm mirror of the weights was found but integrating
it was blocked as untrusted, so container renders still use the espeak-ng fallback. On the Mac, Kokoro `am_adam` is used.
