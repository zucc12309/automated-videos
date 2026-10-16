# EP. 001 · I pasted a script and got back a finished short

Mimo Found This on GitHub · repository: https://github.com/harry0703/MoneyPrinterTurbo
Demo status: **run-in-sandbox** (the project's own code was run in the build environment; the picture re-draws that run)

| Scene | Start | Length | Narration |
|---|---|---|---|
| hook | 0.00s | 3.40s | An open-source tool put this whole short together. |
| discovery | 3.40s | 2.87s | And I found the project on GitHub. |
| demo | 6.27s | 6.63s | Paste a script. It adds the voice, subtitles and music, and cuts the clips together. |
| tech | 12.90s | 4.60s | No script? Plug in your own AI key, and it writes one. |
| payoff | 17.50s | 5.47s | Would you actually use this? Follow Mimo for more GitHub discoveries. |

53 words, 159 wpm while speaking.

## Verified features shown

- **VOICE** (verified-run): Turns the script into a voice-over (here through its Kokoro provider; Edge, Azure and other voices in source). — evidence: run: 'kokoro tts succeeded' -> audio.mp3; app/services/voice.py:2789 kokoro_tts, :1525 azure_tts_v1
- **SUBTITLES** (verified-run): Writes sentence-timed subtitles and burns them into the video. — evidence: run: subtitle.srt with 4 cues, visible in final-1.mp4; app/services/task.py:643, voice.py:3658
- **MUSIC** (verified-run): Mixes a background track under the voice. — evidence: run: --bgm-type random; final mix has no silences where the voice-only track has 3; app/services/video.py:877 get_bgm_file
- **EDIT** (verified-run): Cuts and fits the clips to a 1080x1920 vertical video that matches the voice length. — evidence: run: 'combining video' / 'generating video' -> final-1.mp4 1080x1920 10.0 s; app/services/video.py:965 combine_videos, :1558 generate_video
- **SCRIPT** (verified-source): Can write the script (and footage keywords) from a topic using an LLM provider you configure with your own API key. — evidence: app/services/llm.py:880 generate_script, :1009 generate_terms; WebUI 'Generate Script & Keywords with AI' button (screenshot)
- **WEB UI · CLI · API** (verified-run): Has a web UI, a command line and an HTTP API. — evidence: WebUI run and screenshotted on 127.0.0.1:8501; cli.py run; app/controllers/v1/video.py:212 POST /videos (source)
