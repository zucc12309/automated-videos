# Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `health_check → narration_engine: espeak (fallback …)` | Kokoro / torch not installed | `.venv/bin/pip install -r requirements.lock.txt`; first run downloads `hexgrad/Kokoro-82M` from Hugging Face |
| `narration_engine: unavailable` | neither Kokoro nor espeak-ng | `brew install espeak-ng` and/or install Kokoro |
| `decisions.json`: `ollama … not running` → template | Ollama not running / model not pulled | `ollama serve`; `ollama pull <config.model>` (config says `qwen2.5:14b`) |
| `claude … ANTHROPIC_API_KEY is not set` | no API key | put `ANTHROPIC_API_KEY=…` in `.env` (see `.env.example`); install `requirements-claude.lock.txt` |
| `claude … paid generation disabled` | master switch off | set `budget.allow_paid_generation: true` |
| `explicit approval policy and no approved budget` | no approval on the job | `approved_budget_usd` on `create_hybrid_video`, or `approve_generation(job_id, max_usd)` |
| job `awaiting_approval` | `on_missing_approval: "pause"` | `get_video_report` → `approvals.pending`; then `approve_generation` (resumes automatically) |
| cinematic scene `qa.status: fallback` | provider disabled/unavailable, budget, approval, failure | read the reason in `storyboard.json → scenes[].qa.issues` and `decisions.json` |
| `previous submit outcome unknown` | worker died between submit and recording the id | check the request in your Higgsfield dashboard; clear that entry in `generation_journal.json` only after reconciling |
| job `failed`, `Mandatory QA checks failed after repairs: true_peak` | loudness/peak still out of range | `repair_video(job_id)`; inspect `qa/audio.json` |
| job `failed`, `Worker stopped unexpectedly` (`resumable: true`) | crash/reboot during work | `resume_job(job_id)` — finished stages are reused |
| Remotion: browser fails to launch | Chromium missing on this machine | `node_modules/.bin/remotion browser ensure`, or set `REMOTION_BROWSER_EXECUTABLE` |
| `npm run typecheck` errors | TS change broke a layout | fix before rendering; CI-style check is `node_modules/.bin/tsc -p tsconfig.json` |
| Component forge `rejected` | static scan / typecheck / render / blank screenshot | see `src/studio/generated/registry.json → steps` |
| Text with `…` in the video | copy longer than a layout's capacity | QA flags it (`text_fits`); repair shortens at word boundaries |
| `No fresh unused topic found` | feeds unreachable or all used | check `discover_topics` errors; supply a manual `topic` or a `plan` |

Logs: `data/jobs/<id>/worker.log` (render progress, tracebacks), `status.json → history` (phase timeline).
Never paste `.env` contents into issues; reports and MCP responses are passed through `security.redact`.
