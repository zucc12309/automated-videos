# EP. 001 · This GitHub repo turns a topic into a video

Mimo Found This on GitHub · repository: https://github.com/harry0703/MoneyPrinterTurbo
Demo status: **project-showcase** (official output examples published by the project itself (shown muted and credited); the features they show were also verified in source or by a local run)

| Scene | Start | Length | Narration |
|---|---|---|---|
| hook | 0.00s | 4.13s | This GitHub repo turns a topic into a finished video. |
| discovery | 4.13s | 2.53s | It's called MoneyPrinterTurbo. |
| demo | 6.67s | 7.50s | Give it a topic. It writes the script, finds footage, adds voice and subtitles, then edits the video. |
| tech | 14.17s | 4.90s | It's open source. Use your own AI key, or a local model. |
| payoff | 19.07s | 5.50s | Would you let AI make your next Reel? Follow Mimo for more GitHub discoveries. |

57 words, 158 wpm while speaking.

## Verified features shown

- **FOOTAGE** (verified-source): Searches stock-footage libraries (Pexels, Pixabay and others) for clips that match the script and downloads them. — evidence: app/services/material.py:339 search_videos_pexels, :445 search_videos_pixabay, :2134 download_videos; visible in the official demos (not run here: stock APIs blocked)
- **VOICE** (verified-run): Turns the script into a voice-over (here through its Kokoro provider; Edge, Azure and other voices in source). — evidence: run: 'kokoro tts succeeded' -> audio.mp3; app/services/voice.py:2789 kokoro_tts, :1525 azure_tts_v1
- **SUBTITLES** (verified-run): Writes sentence-timed subtitles and burns them into the video. — evidence: run: subtitle.srt with 4 cues, visible in final-1.mp4; app/services/task.py:643, voice.py:3658
- **MUSIC** (verified-run): Mixes a background track under the voice. — evidence: run: --bgm-type random; final mix has no silences where the voice-only track has 3; app/services/video.py:877 get_bgm_file
- **EDIT** (verified-run): Cuts and fits the clips to a 1080x1920 vertical video that matches the voice length. — evidence: run: 'combining video' / 'generating video' -> final-1.mp4 1080x1920 10.0 s; app/services/video.py:965 combine_videos, :1558 generate_video
- **SCRIPT** (verified-source): Can write the script (and footage keywords) from a topic using an LLM provider you configure with your own API key. — evidence: app/services/llm.py:880 generate_script, :1009 generate_terms; WebUI 'Generate Script & Keywords with AI' button (screenshot)
- **WEB UI · CLI · API** (verified-run): Has a web UI, a command line and an HTTP API; runs on your own machine. — evidence: WebUI run and screenshotted on 127.0.0.1:8501; cli.py run; app/controllers/v1/video.py:212 POST /videos (source)
- **LOCAL MODEL** (verified-source): Script writing can use your own API key for one of ~37 LLM providers (OpenAI, Gemini, DeepSeek, Anthropic, …) or a local model through Ollama. — evidence: app/models/llm_provider.py LLM_PROVIDER_REGISTRY (openai, gemini, deepseek, anthropic, ollama, …); app/services/llm.py:880 generate_script
- **OPEN SOURCE** (verified-source): MIT licensed, Python. — evidence: LICENSE (MIT); pyproject.toml license = MIT, requires-python >= 3.11
