# EP. 001 · Script in, short out: an open-source video maker

Mimo Found This on GitHub · repository: https://github.com/harry0703/MoneyPrinterTurbo
Demo status: **project-showcase** (official output examples published by the project itself (shown muted and credited); the features they show were also verified in source or by a local run)

| Scene | Start | Length | Narration |
|---|---|---|---|
| hook | 0.00s | 3.77s | An open-source tool made both of these videos. |
| discovery | 3.77s | 2.93s | And I found the project on GitHub. |
| demo | 6.70s | 7.10s | Paste a script. It finds the footage, adds voice, subtitles and music, and edits it. |
| tech | 13.80s | 4.30s | No script? Add your AI key, and it writes one. |
| payoff | 18.10s | 5.57s | Would you actually use this? Follow Mimo for more GitHub discoveries. |

51 words, 148 wpm while speaking.

## Verified features shown

- **FOOTAGE** (verified-source): Searches stock-footage libraries (Pexels, Pixabay and others) for clips that match the script and downloads them. — evidence: app/services/material.py:339 search_videos_pexels, :445 search_videos_pixabay, :2134 download_videos; visible in the official demos (not run here: stock APIs blocked)
- **VOICE** (verified-run): Turns the script into a voice-over (here through its Kokoro provider; Edge, Azure and other voices in source). — evidence: run: 'kokoro tts succeeded' -> audio.mp3; app/services/voice.py:2789 kokoro_tts, :1525 azure_tts_v1
- **SUBTITLES** (verified-run): Writes sentence-timed subtitles and burns them into the video. — evidence: run: subtitle.srt with 4 cues, visible in final-1.mp4; app/services/task.py:643, voice.py:3658
- **MUSIC** (verified-run): Mixes a background track under the voice. — evidence: run: --bgm-type random; final mix has no silences where the voice-only track has 3; app/services/video.py:877 get_bgm_file
- **EDIT** (verified-run): Cuts and fits the clips to a 1080x1920 vertical video that matches the voice length. — evidence: run: 'combining video' / 'generating video' -> final-1.mp4 1080x1920 10.0 s; app/services/video.py:965 combine_videos, :1558 generate_video
- **SCRIPT** (verified-source): Can write the script (and footage keywords) from a topic using an LLM provider you configure with your own API key. — evidence: app/services/llm.py:880 generate_script, :1009 generate_terms; WebUI 'Generate Script & Keywords with AI' button (screenshot)
- **WEB UI · CLI · API** (verified-run): Has a web UI, a command line and an HTTP API. — evidence: WebUI run and screenshotted on 127.0.0.1:8501; cli.py run; app/controllers/v1/video.py:212 POST /videos (source)
