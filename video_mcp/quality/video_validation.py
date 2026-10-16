"""Technical validation with ffprobe/ffmpeg. Every check here is deterministic."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


def _ffmpeg_filter(path: Path, args: list[str], timeout=900) -> str:
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), *args, "-f", "null", "-"],
                         capture_output=True, text=True, timeout=timeout)
    return out.stderr


def probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                         capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        return {}
    return json.loads(out.stdout)


def intervals(text: str, start_key: str, end_key: str) -> list[tuple[float, float]]:
    starts = [float(x) for x in re.findall(rf"{start_key}:\s*([\d.]+)", text)]
    ends = [float(x) for x in re.findall(rf"{end_key}:\s*([\d.]+)", text)]
    return [(s, ends[i] if i < len(ends) else -1.0) for i, s in enumerate(starts)]


def technical(path: Path, *, width: int, height: int, fps: int, expected_seconds: float | None, dark_theme: bool = False) -> dict:
    checks: list[dict] = []

    def add(name, passed, detail, mandatory=True):
        checks.append({"check": name, "passed": bool(passed), "detail": detail, "mandatory": mandatory, "basis": "deterministic"})

    info = probe(path)
    video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {})
    audio = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), {})
    duration = float(info.get("format", {}).get("duration") or 0)
    add("readable", bool(info), "ffprobe parsed the container" if info else "ffprobe failed")
    add("resolution", video.get("width") == width and video.get("height") == height, f"{video.get('width')}x{video.get('height')} (want {width}x{height})")
    add("aspect_ratio", bool(video.get("height")) and abs(video.get("width", 0) / video["height"] - width / height) < .01 if video.get("height") else False,
        f"{video.get('display_aspect_ratio', 'n/a')}")
    num, _, den = (video.get("r_frame_rate") or "0/1").partition("/")
    rate = float(num) / float(den or 1) if num else 0
    add("frame_rate", abs(rate - fps) < .05, f"{rate:.3f} fps (want {fps})")
    add("duration", duration > 1 and (expected_seconds is None or abs(duration - expected_seconds) <= .6),
        f"{duration:.2f}s" + (f" (expected {expected_seconds:.2f}s)" if expected_seconds else ""))
    add("audio_present", bool(audio), f"{audio.get('codec_name', 'none')} {audio.get('sample_rate', '')}")
    decode = _ffmpeg_filter(path, ["-v", "error"])
    errors = [line for line in decode.splitlines() if line.strip() and not line.startswith(("Input", "  "))]
    add("decode_integrity", not errors, "clean full decode" if not errors else errors[0][:200])
    # Black frames: a frame is "black" when 99.5% of pixels are below 5% luma. Dark themes sit above that floor.
    black = intervals(_ffmpeg_filter(path, ["-vf", "blackdetect=d=0.3:pic_th=0.995:pix_th=0.05", "-an"]), "black_start", "black_end")
    add("black_frames", not black, f"{len(black)} black segment(s): {black[:4]}" if black else "none")
    freeze = intervals(_ffmpeg_filter(path, ["-vf", "freezedetect=n=0.0008:d=3.5", "-an"]), "freeze_start", "freeze_end")
    add("frozen_frames", not freeze, f"{len(freeze)} frozen segment(s) >= 3.5s: {freeze[:4]}" if freeze else "none", mandatory=False)
    silence = []
    if audio:
        silence = [(s, e) for s, e in intervals(_ffmpeg_filter(path, ["-af", "silencedetect=noise=-50dB:d=1.2", "-vn"]),
                                                 "silence_start", "silence_end") if s < duration - 1.5]
    add("unexpected_silence", not silence, f"{silence[:4]}" if silence else "none", mandatory=False)
    return {"passed": all(c["passed"] for c in checks if c["mandatory"]), "checks": checks, "duration_seconds": duration,
            "black_segments": black, "freeze_segments": freeze, "silence_segments": silence,
            "width": video.get("width"), "height": video.get("height"), "has_audio": bool(audio), "fps": rate}
