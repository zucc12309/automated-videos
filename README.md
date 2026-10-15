# Local Video MCP

A local stdio MCP server for your MacBook. It discovers topics from public RSS feeds, writes English scripts using a local Ollama model, synthesizes US English speech with Kokoro, and renders premium editorial-style vertical explainers using Remotion. No API keys or paid cloud generation services are used.

## Installed on this Mac

- MCP name: `local-video`
- Launcher: `/Users/priyanshupatel/Downloads/VIDEOS/local-video-mcp/run-server.sh`
- Python: isolated `.venv` using Python 3.12
- Local LLM: existing `qwen2.5:7b` via Ollama on `127.0.0.1:11434`
- Voice: Kokoro `af_heart`, US English, running locally
- Output: 1080 × 1920, 30 fps, H.264 MP4 with audio
- Initial niche: AI tools and practical coding; edit `config.json` to change it

The server is registered in Codex's MCP configuration. Open a fresh chat/reload the app if the new tools are not visible. The host starts the server on demand; no public port or tunnel is used. Ollama is started on localhost if needed. A video worker continues after the MCP client disconnects.

Try: **“Use local-video to discover topics, choose one useful topic, and make a polished English reel. Poll until it finishes and show me the video.”**

Or: **“Use local-video run_autopilot_once and show the finished video.”**

## Tools

| Tool | Purpose |
|---|---|
| `health_check` | Check local dependencies and model availability |
| `discover_topics` | Fetch configured public feeds and rank recent unused topics |
| `create_video` | Render a supplied scene plan, without calling a language model |
| `create_video_from_topic` | Write and render a previously discovered topic with local Ollama |
| `run_autopilot_once` | Discover → script → narrate → animate → save, without intermediate input |
| `job_status` | Get progress, error details, and completed file paths |
| `list_videos` | List recent jobs |

Long work runs in a separate process so MCP calls return quickly. One heavy job runs at a time. Completed topic IDs are excluded from future discovery. Failed jobs remain inspectable and do not mark a topic as used.

## Command line

From this directory:

```sh
.venv/bin/local-video health
.venv/bin/local-video discover
.venv/bin/local-video autopilot
.venv/bin/local-video status JOB_ID
.venv/bin/local-video render examples/first-reel.json
npm run studio
```

The example is a curated technical demo. Autopilot instead uses a newly discovered RSS item and the local model. Neither mode publishes to social media.

## Content formats

Autopilot alternates between two formats (`formats` in `config.json`):

- **roundup**: searches GitHub for fresh, high-star repos for each entry in `repo_themes` (Claude Code repos, Codex/agent skills, MCP servers, agent repos). It reads their readmes and scripts a numbered "N repos you should install" reel. Star counts, names and descriptions on screen come from the GitHub API, not from the model. Featured repos are not repeated.
- **story**: picks a recent item from `feeds` (Simon Willison, TechCrunch AI, Hacker News, GitHub and Hugging Face blogs), fetches the full article text, and scripts a numbered "N facts" breakdown. Items with only a headline are skipped.

Scripts are written by `model` (`qwen2.5:14b`) with prompts in `video_mcp/prompts.py`. Every reel has a hook, numbered items, then a recap and call to action.

## Visual styles

The default `studio` engine (`src/studio/`) follows `reports/Reel motion and design practices.md` one folder up:

- **Variety engine** (`video_mcp/variety.py`): each job picks a palette (8), background treatment (6), motion temperament (snappy springs, smooth Carbon curves, or slow editorial), caption style (pill, bold, or editorial), 3 of 5 transitions (whip, zoom, push, mask, hard cut with punch), outfit, music key and tempo, and camera intensity. Choices are seeded from the job ID and penalized if used in the last few videos (`data/variety.json`).
- **Beats**: each line is split at punctuation into 1.3–3 s beats from Kokoro's word timestamps, so something changes every 1.5–3 s. Each beat gets one of 17 layouts: hero word, big number, quote, character close-up, list stack, steps, compare, repo card, terminal, chips, star meter, phone mockup, chat, node graph, hook stack, fact stamp, recap. No layout plays twice in a row, each is used at most twice, and the final beat loops back to the opening frame.
- **Camera and motion**: a slow push-in per beat, a zoom punch timed just before the stressed word, Carbon easing and Remotion springs, and staggered reveals.
- **Layout and captions**: text stays inside the cross-platform safe box (x 120–960, y 290–1248), with 2–4 word captions around y 1100. The hook is readable on frame 0.
- **Character** (`src/Character.tsx`): rounded primitives only, pill eyes with off-center pupils, and oversized glasses as the signature. Nine mouth shapes are driven by Kokoro phonemes, with jaw size scaled by loudness. Blinks are motivated, idle motion comes from seeded noise, the hair lags the head, and nods land on stressed words. Gestures are chosen per beat and lead the beat by 5 frames: pointing at real on-screen content, counting, shrugging, presenting, waving, thumbs-up. The character also moves between anchor positions with a hop.

Older styles (`paper`, `editorial`, `kinetic`, `mascot`, `fieldnotes`) still work. Set `style` in a plan or `styles` in `config.json` to use them.

## Voice and sound

Narration uses Kokoro `voice` (`am_adam`) at `voice_speed`. Sound effects each have one job: a whoosh on moving transitions, a pop on entrances, an impact on the stressed word, a stamp, counter ticks, and a chime on the recap. The procedural music bed changes key and tempo per video and ducks under the voice using the word timings. The final mix is mastered to −14 LUFS / −1 dBTP. Set `music: false` to disable music.

## Files and configuration

Each job has a directory under `data/jobs/JOB_ID/`:

- `video.mp4`, `poster.jpg`: final output and preview
- `plan.json`, `props.json`: editable script and timed scene data
- `topic.json`: source excerpt, when discovered automatically
- `checks.json`, `provenance.json`: technical checks, source URLs and model information
- `status.json`, `worker.log`: progress and diagnostics

Scene audio is in `public/jobs/JOB_ID/`. Models are cached by Hugging Face and Ollama. Do not remove audio while a render is in progress.

Edit `config.json` for feeds, keywords, freshness, voice and the installed Ollama model. Narration, on-screen text, and word-highlight captions are generated in English. The visual style uses a dark editorial palette, restrained motion, animated insight cards, subtle interface sounds, and short alternating horizontal push/slide scene transitions. Change `src/index.tsx` for branding, transitions, and animation.

## Autopilot and scheduling

`run_autopilot_once` performs a complete unattended production run. A repeating schedule is **not enabled** until a cadence is selected. The Mac must be awake; topic discovery needs an internet connection. The renderer and cached speech/language models run locally. This server does not reuse a ChatGPT subscription or call an AI cloud API.

## Quality boundaries

- This is an original editorial explainer template, not an exact reproduction of the reference's human character or hand-crafted scene choreography.
- Topic ranking is keyword relevance + freshness, not a claim to measure social virality.
- Scripts use RSS titles/excerpts, not full-article verification. Prompts constrain claims and retain sources; a local language model can still make mistakes. Review facts before publication.
- Kokoro's pronunciation needs a listening review, especially names and acronyms. Narration is synthesized per scene and normalized for consistent playback level. Captions use the exact spoken text, with word timing estimated by word length rather than forced alignment. Subtle synthesized UI cues accompany scene and point reveals.
- Technical validation checks dimensions, presence of audio, and nonzero duration. It does not certify factual accuracy, natural speech, or every layout.
- No background music is included. The current audio track is narration only.

## Repositories and licenses

| Component | Upstream | License / role |
|---|---|---|
| MCP SDK | https://github.com/modelcontextprotocol/python-sdk | MIT; tool protocol |
| Ollama | https://github.com/ollama/ollama | MIT; local model runtime |
| Qwen2.5 7B | https://huggingface.co/Qwen/Qwen2.5-7B-Instruct | Apache 2.0; script model |
| Kokoro | https://github.com/hexgrad/kokoro | Apache 2.0; local speech |
| Kokoro weights | https://huggingface.co/hexgrad/Kokoro-82M | Apache 2.0; multilingual voice presets |
| Remotion | https://github.com/remotion-dev/remotion | Special license; free eligibility depends on usage/team; see upstream LICENSE.md |
| FFmpeg | https://ffmpeg.org | LGPL/GPL depending on build; media processing |
| feedparser | https://github.com/kurtmckee/feedparser | BSD; RSS/Atom parsing |

No paid service is configured. Remotion's company/service licensing rules still apply if the project becomes a larger business or hosted product.

## Reinstall / test

```sh
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.lock.txt
.venv/bin/pip install -e . --no-deps
npm ci
brew install ffmpeg espeak-ng ollama
node_modules/.bin/remotion browser ensure
.venv/bin/python -m pytest -q
```

The model `qwen2.5:7b` must be available in Ollama. On another Mac, update the Node path in `run-server.sh` and register its absolute path with your MCP client. Initial package, browser, and speech-weight downloads require internet, but no account/key.

To remove the Codex registration: `codex mcp remove local-video`. This leaves your generated files intact.
