# CTA and resource workflow

## What the video says

`video_mcp/creative/cta.py` chooses the keyword from the content type. The keywords are defined in `brand/series.json` and
`brand/cta_templates.json`.

| Keyword | Content | Spoken line (truthful mode) |
|---|---|---|
| LINK | repository roundups | "Want all {count} repos? Comment LINK for the list." |
| PROMPT | vibe-coding tips | "Want the full template? Comment PROMPT." |
| GUIDE | tutorials, agents / MCP | "Want the step-by-step? Comment GUIDE." |
| CODE | code examples, debugging | "Want the example code? Comment CODE." |
| TOOLS | tool comparisons | "Want the full list? Comment TOOLS." |

The outro is rewritten so that four things agree:

- the spoken line;
- the on-screen keyword (`SignatureCTA`);
- the secondary line;
- the fulfilment note.

The outro gets a "pause" pace, so the keyword lands in silence, and the loop tail never swallows a short CTA (`_noLoop`).

## The video never promises a DM

Nothing in this repository sends direct messages. No platform integration is configured, and none is simulated. So:

- `brand/cta_templates.json → fulfillment.dm_delivery_enabled` is `false`.
- `config.json → brand_profile.cta_dm_delivery_enabled` is `false`.
- Both must be true before a "DM" narration template is used. Setting them to true is only appropriate once an authorized, working
  delivery mechanism exists, such as an official platform API integration that you set up and tested.
- QA check `cta_truthful` fails any render whose narration or secondary line promises a DM or "I'll send you" while delivery is off.

No scraping, no reuse of unofficial sessions, and no simulated comment automation is implemented, by design.

## What gets prepared

After every successful render, `cta.write_resources` writes `data/jobs/<id>/resources/`. The demos copy it to `demos/v22/<X>/resources/`.

| File | Contents |
|---|---|
| `resource_manifest.json` | keyword, fulfilment mode (`manual`), `dm_promised_in_video: false`, every item with its URL and what verified it |
| `guide.md` | title, core message, numbered list of repositories / sources with URLs and descriptions |
| `prompt.md` | vibe_coding only: the weak prompt and the better template |
| `example_code/example.txt` | when the video shows code: the snippet, labelled "not executed by this pipeline" |
| `dm_message.txt` | a ready-to-paste reply for people who comment the keyword |

Only verified data goes in:

- **Repositories:** their GitHub metadata from the topic.
- **Sources:** the storyboard's source list.

## Manual sending (today)

1. Post the reel.
2. When someone comments the keyword, open `resources/dm_message.txt` for that video.
3. Review it, then send it yourself from the platform app.

Before sending, check that the links still work.
