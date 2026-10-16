"""Reference-driven visual QA: measurable style statistics of a render vs. the FIELDNOTES reference (brand/reference/).

Deterministic pixel statistics only: ground colour, mean luminance, accent/ink share, cut rate. A side-by-side contact
sheet (reference row over render row) is produced for human review. No model judgment is involved; anything about taste
is left to the person reviewing the sheet.
Usage: python -m video_mcp.quality.reference_compare <video.mp4> [out_dir]
       python -m video_mcp.quality.reference_compare --save-reference <reference.mp4>
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "brand" / "reference"
W, H = 108, 192          # analysis size (1/10 of 1080x1920)
EVENT_DIFF = 2.5        # mean |Δ| (0–255) between 4 fps samples that counts as a visual change
TOLERANCE = {"ground_delta": 18, "luma_ratio": (0.6, 1.6), "cuts_ratio": (0.5, 2.0)}


def _duration(video: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                         capture_output=True, text=True, check=True).stdout
    return float(out)


def _frames(video: Path, count: int = 24) -> np.ndarray:
    fps = count / _duration(video)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"fps={fps:.5f},scale={W}:{H}", "-frames:v", str(count),
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3).astype(np.float32)


def _changes(video: Path, fps: int = 4) -> tuple[int, float]:
    """(change events, mean frame difference) at 4 fps. Blur dissolves on a dark ground defeat scene-cut detection, so a
    'change event' is a sample whose mean absolute difference from the previous sample exceeds EVENT_DIFF."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"fps={fps},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True, check=True).stdout
    g = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)
    d = np.abs(np.diff(g, axis=0)).mean(axis=(1, 2)) if len(g) > 1 else np.zeros(1)
    peaks = (d > EVENT_DIFF) & np.r_[True, d[1:] > d[:-1]] & np.r_[d[:-1] >= d[1:], True]
    return int(peaks.sum()), float(d.mean())


def stats(video: Path) -> dict:
    frames = _frames(video)
    luma = frames @ np.array([.2126, .7152, .0722], np.float32)
    dark = frames[luma < np.percentile(luma, 50)]
    ground = np.median(dark, axis=0)
    bright = (luma > 200).mean()
    sat = (frames.max(-1) - frames.min(-1))
    accent = ((sat > 60) & (luma > 80)).mean()
    dur = _duration(video)
    cuts, motion = _changes(video)
    return {"motion_mean_diff": round(motion, 2), "duration_s": round(dur, 2), "ground_rgb": [int(x) for x in ground], "mean_luma": round(float(luma.mean()), 1),
            "ink_share": round(float(bright), 4), "accent_share": round(float(accent), 4), "change_events": cuts,
            "changes_per_10s": round(10 * cuts / max(dur, .1), 2)}


def strip(video: Path, dest: Path, count: int = 8, width: int = 180) -> None:
    fps = count / _duration(video)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-vf", f"fps={fps:.5f},scale={width}:-1,tile={count}x1", "-frames:v", "1",
                    str(dest)], check=True)


def save_reference(video: Path) -> dict:
    REF.mkdir(parents=True, exist_ok=True)
    data = {"source": "Reference A (FIELDNOTES reel supplied by the owner)", **stats(video)}
    (REF / "reference_a_stats.json").write_text(json.dumps(data, indent=1))
    strip(video, REF / "reference_a_strip.jpg")
    return data


def compare(video: Path, out_dir: Path) -> dict:
    ref_file = REF / "reference_a_stats.json"
    if not ref_file.exists():
        return {"available": False, "note": "no reference stats saved (run --save-reference with the reference reel)"}
    ref = json.loads(ref_file.read_text())
    got = stats(video)
    delta = float(np.abs(np.array(ref["ground_rgb"]) - np.array(got["ground_rgb"])).max())
    luma_ratio = got["mean_luma"] / max(ref["mean_luma"], .1)
    cuts_ratio = got["changes_per_10s"] / max(ref["changes_per_10s"], .1)
    checks = [
        {"check": "ground_colour", "passed": delta <= TOLERANCE["ground_delta"], "detail": f"max channel delta {delta:.0f} (≤ {TOLERANCE['ground_delta']})"},
        {"check": "luminance", "passed": TOLERANCE["luma_ratio"][0] <= luma_ratio <= TOLERANCE["luma_ratio"][1],
         "detail": f"mean luma {got['mean_luma']} vs reference {ref['mean_luma']} (ratio {luma_ratio:.2f})"},
        {"check": "change_rate", "passed": TOLERANCE["cuts_ratio"][0] <= cuts_ratio <= TOLERANCE["cuts_ratio"][1],
         "detail": f"{got['changes_per_10s']} vs reference {ref['changes_per_10s']} visual changes per 10 s (ratio {cuts_ratio:.2f}); "
                   f"motion {got['motion_mean_diff']} vs {ref['motion_mean_diff']}"},
    ]
    out_dir.mkdir(parents=True, exist_ok=True)
    mine = out_dir / "_render_strip.jpg"
    strip(video, mine)
    sheet = out_dir / "reference_side_by_side.jpg"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(REF / "reference_a_strip.jpg"), "-i", str(mine), "-filter_complex",
                    "[0][1]scale2ref=w=iw:h=ow/mdar[a][b];[a][b]vstack", str(sheet)], check=False)
    if not sheet.exists():
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(REF / "reference_a_strip.jpg"), "-i", str(mine), "-filter_complex", "vstack",
                        str(sheet)], check=True)
    mine.unlink(missing_ok=True)
    return {"available": True, "basis": "deterministic pixel statistics; taste judgments need human review of the side-by-side sheet",
            "reference": ref, "render": got, "checks": checks, "side_by_side": str(sheet)}


if __name__ == "__main__":
    if sys.argv[1] == "--save-reference":
        print(json.dumps(save_reference(Path(sys.argv[2])), indent=1))
    else:
        out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(sys.argv[1]).parent / "qa"
        result = compare(Path(sys.argv[1]), out)
        (out / "reference_compare.json").write_text(json.dumps(result, indent=1))
        print(json.dumps(result, indent=1))
