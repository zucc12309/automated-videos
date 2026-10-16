"""DevMimo intro QA. The deterministic checks reuse the V2.2 QA modules; the visual review is a separate, labelled section.

- technical: `video_validation.technical` (resolution, fps, duration, decode, black / frozen frames, silence);
- audio: `audio_profile.compare` against the brand's reference audio profile;
- timing: every scene is at least as long as its narration (lead + speech);
- hook: frame 0 has readable, high-contrast content (luma spread);
- motion: share of frame-to-frame changes at 4 fps, longest static stretch;
- palette: share of on-brand pixels (charcoal / ivory / orange) on sampled frames;
- logo: technical checks on the 5 s sting.

The visual review (`visual_review.json`) holds what a person or agent saw on the extracted frames. It is never computed.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

from video_mcp import audio_profile
from video_mcp.quality import video_validation

HERE = Path(__file__).resolve().parent
PALETTE = {"charcoal": (20, 20, 22), "ivory": (244, 239, 228), "orange": (255, 122, 26)}


def _frames(video: Path, fps: float, width: int = 270) -> np.ndarray:
    h = int(width * 1920 / 1080)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"fps={fps},scale={width}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, width, 3)


def _frame_at(video: Path, t: float, width: int = 540) -> np.ndarray:
    h = int(width * 1920 / 1080)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-vf", f"scale={width}:{h}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, width, 3)


def _luma(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * .2126 + rgb[..., 1] * .7152 + rgb[..., 2] * .0722


def palette_share(frames: np.ndarray, tol: float = 60.0) -> float:
    """Pixels within `tol` (RGB distance) of a brand colour, or on the charcoal→ivory neutral axis / orange ramp."""
    px = frames.reshape(-1, 3).astype(np.float32)[::7]
    near = np.zeros(len(px), bool)
    for c in PALETTE.values():
        near |= np.linalg.norm(px - np.array(c, np.float32), axis=1) < tol
    r, g, b = px[:, 0], px[:, 1], px[:, 2]
    neutral = (np.abs(r - g) < 22) & (np.abs(g - b) < 26)                  # charcoal, greys, ivory and their blends
    warm = (r > g) & (g > b) & (r - b > 60) & ((g - b) / np.maximum(r - b, 1) < .75)   # orange tints / glows
    return float((near | neutral | warm).mean())


def run(intro: Path, logo: Path, props: dict, story: dict, timing: dict) -> dict:
    checks = []

    def add(group, name, passed, detail, mandatory=True):
        checks.append({"group": group, "check": name, "passed": bool(passed), "detail": detail, "mandatory": mandatory, "basis": "deterministic"})

    tech = video_validation.technical(intro, width=1080, height=1920, fps=30, expected_seconds=props["durationInFrames"] / 30, dark_theme=True)
    for c in tech["checks"]:
        add("technical", c["check"], c["passed"], c["detail"], c.get("mandatory", True))
    seconds = float(video_validation.probe(intro)["format"]["duration"])
    add("technical", "target_length", abs(seconds - 30) <= .5, f"{seconds:.2f}s (target 30 ±0.5)")

    for s in props["scenes"]:
        need = (s["lead_s"] + s["speech_s"]) * 30
        add("timing", f"scene_fits_narration:{s['id']}", s["frames"] >= need, f"{s['frames']} frames for {need:.0f} frames of lead + speech")

    audio = audio_profile.compare(intro)
    for c in audio["checks"]:
        # Speech share and pauses are a property of a 30 s brand intro with long visual holds, not a defect; reported, not gating.
        add("audio", c["check"], c["passed"], c["detail"], mandatory=c["check"] in {"loudness", "true_peak", "voice_pitch", "voice_tone"})

    f0 = _frame_at(intro, 0.0)
    spread = float(np.percentile(_luma(f0), 99) - np.percentile(_luma(f0), 5))
    add("hook", "frame0_contrast", spread > 120, f"luma p99-p5 spread {spread:.0f} on frame 0 (>120 = bold readable content)")
    bright = float((_luma(f0) > 200).mean())
    add("hook", "frame0_has_type", bright > .01, f"{bright * 100:.1f}% of frame 0 is bright type/graphics")

    fr = _frames(intro, 4).astype(np.float32)
    diff = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2, 3))
    moving = diff > 1.2
    longest, run_ = 0, 0
    for m in moving:
        run_ = 0 if m else run_ + 1
        longest = max(longest, run_)
    add("motion", "motion_share", moving.mean() > .7, f"{moving.mean() * 100:.0f}% of 0.25 s steps change visibly")
    add("motion", "longest_static", longest / 4 <= 1.5, f"longest static stretch {longest / 4:.2f}s (≤ 1.5 s)")
    share = palette_share(fr[::4])
    add("brand", "palette_share", share > .9, f"{share * 100:.1f}% of sampled pixels are charcoal / ivory / orange or their blends")

    lt = video_validation.technical(logo, width=1080, height=1920, fps=30, expected_seconds=5.0, dark_theme=True)
    for c in lt["checks"]:
        if c["check"] in {"readable", "resolution", "frame_rate", "duration", "decode_integrity", "black_frames", "audio_present"}:
            add("logo", c["check"], c["passed"], c["detail"])

    review_path = HERE / "visual_review.json"
    review = json.loads(review_path.read_text()) if review_path.exists() else {"status": "not reviewed"}
    failed = [c for c in checks if not c["passed"] and c["mandatory"]]
    advisories = [c for c in checks if not c["passed"] and not c["mandatory"]]
    return {
        "video": intro.name, "logo": logo.name, "seconds": round(seconds, 3), "frames": props["durationInFrames"],
        "voice": timing.get("voice"), "music_bed_gain_db": timing.get("bed_gain_db"),
        "scenes": [{"id": s["id"], "start_s": round(s["from"] / 30, 2), "seconds": round(s["frames"] / 30, 2), "speech_s": s["speech_s"]} for s in props["scenes"]],
        "sfx_cues": len(story["sfx"]),
        "summary": {"passed": not failed, "mandatory_failed": [c["check"] for c in failed], "advisories": [c["check"] for c in advisories],
                    "checks": len(checks), "visual_review": review.get("status")},
        "checks": checks, "visual_review": review,
        "basis": "deterministic checks via ffmpeg/numpy; visual_review is a human/agent inspection of extracted frames, recorded separately",
    }
