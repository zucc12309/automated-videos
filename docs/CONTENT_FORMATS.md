# Content formats and series

`config.json → formats` lists the formats autopilot may pick. Each format has a series label and a default CTA keyword, both set in
`brand/series.json`. The labels are internal: the masthead shows `FIELDNOTES · <series>`.

| Format / content type | Series label | CTA | Typical structure |
|---|---|---|---|
| `roundup` (GitHub repositories) | REPO RADAR | LINK | hook with avatars → per repo: card → demo (terminal, README, workflow) → recap → CTA |
| `vibe_coding` (prompting tips) | BUILD SMARTER | PROMPT | hook → weak prompt (terminal, confused) → before/after → why it works → expected change → CTA |
| agents / MCP stories | AGENT FILES | GUIDE | hook → architecture hub → steps → code → flow → caution → CTA |
| tools | TOOL DROP | TOOLS | as roundup |
| debugging | THE DEBUG LOG | CODE | hook → failing output → root cause → fix diff → CTA |
| other stories | FIELD REPORT | GUIDE | hook → explanation beats → CTA |

## Hooks

`video_mcp/creative/hooks.py` builds three truthful candidates from the topic data and scores each one. All scores are stored in
`storyboard.json → hook_candidates`.

| Criterion | Weight |
|---|---|
| Clarity | 1.4 |
| Specificity | 1.0 |
| Relevance | 1.0 |
| Curiosity | 0.8 |
| Visual potential | 0.6 |
| Credibility | gate (×0 or ×1) |

A hook is disqualified (scores 0) if it uses hype words or numbers that aren't in the sources.

- **Generated storyboards** open with the best candidate.
- **Supplied storyboards** keep their authored hook; the candidates are still scored and recorded.

The hook is readable on frame 0, and the QA check `hook_frame0` verifies this.

## `vibe_coding`

**Source.** `video_mcp/content/vibe_library.json` is a curated tip library. Each tip has:

- `weak` and `better` prompt lines;
- `why` (three reasons);
- an illustrative `demo` change;
- notes and a documentation source.

Discovery picks unused tips when `vibe_coding` is in `formats`. No network is needed.

**Storyboard.** Without Claude, `director.vibe_storyboard` builds the deterministic six-scene structure shown in the table above.
In claude or hybrid mode, Claude writes it from the same research packet.

**Labelling.** Tips are editorial guidance. The demo diff is illustrative and is never presented as an executed result. The
research packet says so, and `example_code/example.txt` carries the same note.

**Resources.** `resources/` holds `prompt.md`, `example_code/`, `guide.md`, `resource_manifest.json` and `dm_message.txt`. See
`docs/CTA_RESOURCE_WORKFLOW.md`.

## Mixing formats in autopilot

Autopilot (`engine.discover`) merges three candidate sources: roundups, stories and vibe tips. It scores them, skips anything already
published (`history_ids`), and rotates themes. Under the premium style, every video uses the same `fieldnotes-premium` brand. Variety
comes from layouts, series labels and content, not from changing palettes.
