"""Audio QA: loudness, true peak, clipping, per-scene speech presence and caption sync."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path


def loudness(path: Path) -> dict:
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True, timeout=600).stderr
    summary = out[out.rfind("Summary:"):] if "Summary:" in out else out

    def grab(label):
        m = re.search(label + r":\s*(-?[\d.]+|-inf)", summary)
        return float(m.group(1)) if m and m.group(1) != "-inf" else None
    return {"integrated_lufs": grab(r"I"), "lra": grab(r"LRA"), "true_peak_dbtp": grab(r"Peak")}


def analyze(path: Path, narration: list[dict], *, target_lufs: float = -14.0) -> dict:
    checks = []
    loud = loudness(path)

    def add(name, passed, detail, mandatory=False, basis="deterministic"):
        checks.append({"check": name, "passed": bool(passed), "detail": detail, "mandatory": mandatory, "basis": basis})

    lufs, peak = loud["integrated_lufs"], loud["true_peak_dbtp"]
    add("loudness", lufs is not None and abs(lufs - target_lufs) <= 2.0, f"{lufs} LUFS (target {target_lufs} ±2)")
    add("true_peak", peak is not None and peak <= -0.5, f"{peak} dBTP (limit -0.5)", mandatory=True)
    add("clipping", peak is not None and peak < 0, f"true peak {peak} dBTP")
    for i, n in enumerate(narration):
        sync = n.get("sync", {})
        add(f"scene_{i + 1:03d}_caption_sync", sync.get("covered_speech", 0) >= .8,
            f"{sync} via {n.get('timing_source')}", basis="heuristic" if n.get("timing_source") != "kokoro_timestamps" else "deterministic")
    sources = sorted({n.get("timing_source") for n in narration})
    return {"passed": all(c["passed"] for c in checks if c["mandatory"]), "checks": checks, "loudness": loud,
            "timing_sources": sources, "estimated_timings": any(s != "kokoro_timestamps" for s in sources),
            "engines": sorted({n.get("engine") for n in narration})}
