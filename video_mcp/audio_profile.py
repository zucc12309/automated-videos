"""Reference audio profile: measure Reference A's sound and make renders match it.

`measure(video)` returns the same deterministic statistics for any file:
- loudness (integrated, LRA, true peak);
- speech vs. music-bed level;
- quietest-moment floor;
- speech share of the runtime and pause lengths;
- voice pitch (median and p10–p90);
- voice spectrum on speech frames;
- bed brightness.

`brand/audio_profile.json` stores Reference A's measurements together with the render targets derived from them. The pipeline uses
those targets for:
- espeak fallback prosody (variant, pitch, range, pauses);
- an adaptive EQ that moves each narration toward the reference voice spectrum, whichever engine produced it;
- the warm-pad music bed and its level;
- scene tails;
- mastering.

QA writes `qa/audio_profile_compare.json`.

Kokoro `am_adam` (speed 1.05) is the reference voice itself, so its timbre, pitch and pauses are left alone. No model judgment is
involved anywhere.

Usage:
    python -m video_mcp.audio_profile --save-reference <reference.mp4>
    python -m video_mcp.audio_profile <video.mp4>
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "brand" / "audio_profile.json"
SR = 16000
BANDS = {"low": (100, 300), "mid": (300, 2000), "presence": (2000, 5000), "air": (5000, 8000)}
EQ_POINTS = {"low": ("equalizer", 180, 1.2), "mid": ("equalizer", 900, 1.4), "presence": ("equalizer", 3300, 1.2), "air": ("highshelf", 6000, .7)}
EQ_LIMIT_DB = 6.0
EQ_EFFICIENCY = .6     # a peaking/shelf filter moves a band's total energy by roughly 60% of its gain (measured on espeak speech)
TOLERANCE = {"lufs": 1.0, "true_peak_max": -1.0, "bed_minus_speech": 3.0, "f0_median": 12.0, "speech_fraction": .08, "pause_median": .08,
             "band": 3.0, "bed_centroid": 70.0}


def _load(path: Path) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def _db(x):
    return 20 * np.log10(np.maximum(x, 1e-9))


def loudness(path: Path) -> dict:
    out = subprocess.run(["ffmpeg", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    summary = out[out.rfind("Summary:"):]
    get = lambda key: float(m.group(1)) if (m := re.search(rf"{key}:\s+(-?[\d.]+)", summary)) else None
    return {"integrated_lufs": get("I"), "lra_lu": get("LRA"), "true_peak_dbtp": get("Peak")}


def f0_stats(x: np.ndarray, gate_db: float) -> dict:
    win, f0 = int(.04 * SR), []
    for i in range(0, len(x) - win, int(.05 * SR)):
        seg = x[i:i + win]
        if _db(np.sqrt((seg ** 2).mean())) < gate_db:
            continue
        seg = seg - seg.mean()
        ac = np.correlate(seg, seg, "full")[win - 1:]
        lo, hi = int(SR / 350), int(SR / 70)
        k = lo + int(np.argmax(ac[lo:hi]))
        if ac[k] > .3 * ac[0]:
            f0.append(SR / k)
    if not f0:
        return {"f0_median": None, "f0_p10": None, "f0_p90": None}
    return {"f0_median": round(float(np.median(f0)), 1), "f0_p10": round(float(np.percentile(f0, 10)), 1),
            "f0_p90": round(float(np.percentile(f0, 90)), 1)}


def bands(x: np.ndarray) -> dict:
    """Relative band energy (dB vs. total) of a signal."""
    spec = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(len(x), 1 / SR)
    total = spec[f >= 20].sum() + 1e-12
    return {k: round(float(10 * np.log10(spec[(f >= a) & (f < b)].sum() / total + 1e-12)), 1) for k, (a, b) in BANDS.items()}


def analyze_pcm(x: np.ndarray) -> dict:
    hop = int(.02 * SR)
    n = len(x) // hop
    frames = x[:n * hop].reshape(n, hop)
    rms = _db(np.sqrt((frames ** 2).mean(1)))
    p95 = float(np.percentile(rms, 95))
    speech = rms > p95 - 15
    gap = rms < p95 - 20
    runs, cur, length = [], bool(speech[0]), 0
    for s in speech:
        if bool(s) == cur:
            length += 1
        else:
            runs.append((cur, length))
            cur, length = bool(s), 1
    runs.append((cur, length))
    pauses = [l * .02 for s, l in runs if not s and l * .02 >= .12]
    voiced = frames[speech].reshape(-1) if speech.any() else x
    bed = frames[gap]
    bed_centroid = None
    if len(bed):
        win = np.hanning(hop)
        spec = (np.abs(np.fft.rfft(bed * win, axis=1)) ** 2).mean(0)
        f = np.fft.rfftfreq(hop, 1 / SR)
        bed_centroid = round(float((f * spec).sum() / (spec.sum() + 1e-12)))
    return {"duration_s": round(len(x) / SR, 2), "speech_level_db": round(p95, 1),
            "bed_minus_speech_db": round(float(np.median(rms[gap])) - p95, 1) if gap.any() else None,
            "floor_minus_speech_db": round(float(np.percentile(rms, 5)) - p95, 1),
            "speech_fraction": round(float(speech.mean()), 3), "pause_median_s": round(float(np.median(pauses)), 2) if pauses else 0.0,
            "pauses_per_10s": round(10 * len(pauses) / max(len(x) / SR, .1), 2), **f0_stats(x, p95 - 12),
            "voice_bands_db": bands(voiced), "bed_centroid_hz": bed_centroid}


def measure(path: Path) -> dict:
    return {**loudness(path), **analyze_pcm(_load(path))}


def profile() -> dict:
    return json.loads(PROFILE.read_text())


def save_reference(path: Path) -> dict:
    measured = measure(path)
    current = profile() if PROFILE.exists() else {}
    data = {**current, "source": "Reference A (FIELDNOTES reel supplied by the owner)", "measured": measured}
    PROFILE.write_text(json.dumps(data, indent=1))
    return data


def match_eq(pcm: np.ndarray, rate: int, target_bands: dict) -> tuple[str, dict]:
    """ffmpeg filter chain moving this narration's band balance toward the reference voice (each gain clamped to ±6 dB)."""
    x = pcm.astype(np.float32)
    if rate != SR:
        n = int(len(x) * SR / rate)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    got = bands(x)
    # Remove the overall offset so the EQ changes balance, not loudness (loudnorm follows).
    diff = {k: target_bands[k] - got[k] for k in BANDS}
    mean = sum(diff.values()) / len(diff)
    gains = {k: round(float(np.clip((v - mean) / EQ_EFFICIENCY, -EQ_LIMIT_DB, EQ_LIMIT_DB)), 1) for k, v in diff.items()}
    parts = []
    for k, g in gains.items():
        if abs(g) < .5:
            continue
        kind, freq, width = EQ_POINTS[k]
        parts.append(f"highshelf=f={freq}:g={g}:t=q:w={width}" if kind == "highshelf" else f"equalizer=f={freq}:t=q:w={width}:g={g}")
    return ",".join(parts), {"measured": got, "gains_db": gains}


def _frame_db(x: np.ndarray, rate: int) -> np.ndarray:
    hop = int(.02 * rate)
    n = len(x) // hop
    return _db(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)))


def bed_gain_db(narration: list[np.ndarray], music: np.ndarray, rate: int, bed_minus_speech_db: float) -> float:
    """Gain that puts the un-ducked bed `bed_minus_speech_db` under the narration's speech peaks (p95 of 20 ms frames), as measured
    on Reference A. The bed's un-ducked level is its p80 frame level (ducked frames are quieter)."""
    speech = float(np.percentile(np.concatenate([_frame_db(n, rate) for n in narration]), 95))
    bed = float(np.percentile(_frame_db(music, rate), 80))
    return round(speech + bed_minus_speech_db - bed, 2)


def compare(path: Path) -> dict:
    ref = profile()["measured"]
    got = measure(path)
    targets = profile().get("targets", {})
    checks = []

    def add(name, passed, detail):
        checks.append({"check": name, "passed": bool(passed), "detail": detail, "basis": "deterministic"})

    add("loudness", abs((got["integrated_lufs"] or 0) - ref["integrated_lufs"]) <= TOLERANCE["lufs"],
        f"{got['integrated_lufs']} vs reference {ref['integrated_lufs']} LUFS (±{TOLERANCE['lufs']})")
    add("true_peak", (got["true_peak_dbtp"] or 0) <= TOLERANCE["true_peak_max"], f"{got['true_peak_dbtp']} dBTP (≤ {TOLERANCE['true_peak_max']})")
    if got["bed_minus_speech_db"] is not None:
        add("music_bed_level", abs(got["bed_minus_speech_db"] - ref["bed_minus_speech_db"]) <= TOLERANCE["bed_minus_speech"],
            f"bed {got['bed_minus_speech_db']} vs reference {ref['bed_minus_speech_db']} dB under speech (±{TOLERANCE['bed_minus_speech']})")
    if got["bed_centroid_hz"] is not None:
        add("music_bed_warmth", abs(got["bed_centroid_hz"] - ref["bed_centroid_hz"]) <= TOLERANCE["bed_centroid"],
            f"bed centroid {got['bed_centroid_hz']} vs reference {ref['bed_centroid_hz']} Hz (±{TOLERANCE['bed_centroid']})")
    if got["f0_median"]:
        add("voice_pitch", abs(got["f0_median"] - ref["f0_median"]) <= TOLERANCE["f0_median"],
            f"median F0 {got['f0_median']} vs reference {ref['f0_median']} Hz; range {got['f0_p10']}–{got['f0_p90']} vs {ref['f0_p10']}–{ref['f0_p90']}")
    add("speech_share", abs(got["speech_fraction"] - ref["speech_fraction"]) <= TOLERANCE["speech_fraction"],
        f"{got['speech_fraction']} vs reference {ref['speech_fraction']} of the runtime is speech (±{TOLERANCE['speech_fraction']})")
    add("pause_length", abs(got["pause_median_s"] - ref["pause_median_s"]) <= TOLERANCE["pause_median"],
        f"median pause {got['pause_median_s']} vs reference {ref['pause_median_s']} s (±{TOLERANCE['pause_median']})")
    worst = max(BANDS, key=lambda k: abs(got["voice_bands_db"][k] - ref["voice_bands_db"][k]))
    delta = got["voice_bands_db"][worst] - ref["voice_bands_db"][worst]
    add("voice_tone", abs(delta) <= TOLERANCE["band"],
        f"largest band difference: {worst} {delta:+.1f} dB (±{TOLERANCE['band']}); render {got['voice_bands_db']} vs {ref['voice_bands_db']}")
    return {"reference": ref, "render": got, "targets": targets, "checks": checks,
            "basis": "deterministic signal statistics; timbre beyond these numbers needs listening"}


if __name__ == "__main__":
    if sys.argv[1] == "--save-reference":
        print(json.dumps(save_reference(Path(sys.argv[2])), indent=1))
    else:
        print(json.dumps(compare(Path(sys.argv[1])), indent=1))
