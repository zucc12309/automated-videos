"""Minimal OpenAI-compatible speech server on 127.0.0.1:8880 (the contract MoneyPrinterTurbo's [kokoro] provider expects, same as
remsky/Kokoro-FastAPI): POST /v1/audio/speech -> mp3, GET /v1/audio/voices. Backed by kokoro-onnx (Kokoro-82M, Apache-2.0).
Local-only (binds 127.0.0.1). Used to run MoneyPrinterTurbo for EP. 001; see docs/SERIES.md."""
import io, json, subprocess, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))   # repo root: reuse video_mcp.tts model paths
from video_mcp import tts
from kokoro_onnx import Kokoro
model = Kokoro(str(tts.ONNX_DIR / tts.ONNX_FILES[0]), str(tts.ONNX_DIR / tts.ONNX_FILES[1]))

class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        if self.path.rstrip("/").endswith("/audio/voices"):
            return self._send(200, json.dumps({"voices": ["af_heart", "af_bella", "af_nicole", "am_adam", "am_michael", "bf_emma"]}).encode(), "application/json")
        self._send(404, b"{}", "application/json")
    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        pcm, rate = model.create(req["input"], voice=req.get("voice", "af_heart"), speed=float(req.get("speed", 1.0)), lang="en-us")
        wav = (np.clip(np.asarray(pcm), -1, 1) * 32767).astype("<i2").tobytes()
        mp3 = subprocess.run(["ffmpeg", "-v", "error", "-f", "s16le", "-ar", str(rate), "-ac", "1", "-i", "-", "-b:a", "192k", "-f", "mp3", "-"],
                             input=wav, capture_output=True, check=True).stdout
        self._send(200, mp3, "audio/mpeg")
    def log_message(self, *a): pass

HTTPServer(("127.0.0.1", 8880), H).serve_forever()
