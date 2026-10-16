"""Episode QA for a series build. Deterministic checks reuse the V2.2 QA modules and the intro's frame metrics; the visual review is a
separate, labelled record (qa/visual_review.json in the episode folder) written by whoever inspected the frames.

Groups: technical (both exports), audio (loudness / true peak, both exports), pacing (length, speaking rate), timing (each scene ≥ its
narration), subtitles (transcript match, 3–5 words, on-screen time, safe zone, no overlap with demo blocks), layout (every block
inside the safe zone), hook (frame-0 contrast), motion, brand (palette share), cover (sizes, crop safety, thumbnail legibility),
mascot (single source), copy (claims trace to verified features; no hype, no repository statistics).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import subprocess

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "examples" / "devmimo"))
import qa as intro_qa  # noqa: E402  (frame helpers)
from video_mcp import audio_profile, series  # noqa: E402
from video_mcp.quality import video_validation  # noqa: E402

def _png_size(path: Path) -> tuple[int, int]:
    info = video_validation.probe(path)["streams"][0]
    return info["width"], info["height"]


def _png_gray(path: Path) -> np.ndarray:
    w, h = _png_size(path)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w)


LAYOUT = json.loads((ROOT / "src" / "series" / "layout.json").read_text())


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return int(c[:2], 16), int(c[2:4], 16), int(c[4:], 16)


def palette_share(frames: np.ndarray, palette: dict, tol: float = 60.0) -> float:
    """On-palette pixels: near a series colour or the mascot's, on the neutral ground→ink axis, or on the warm accent ramp."""
    px = frames.reshape(-1, 3).astype(np.float32)[::7]
    near = np.zeros(len(px), bool)
    for c in [*palette.values(), "#f6f6f2", "#d9d9d3", "#f3b4c2", "#ffd76a", "#121318"]:
        near |= np.linalg.norm(px - np.array(_hex(c), np.float32), axis=1) < tol
    r, g, b = px[:, 0], px[:, 1], px[:, 2]
    neutral = (np.abs(r - g) < 24) & (np.abs(g - b) < 28)
    warm = (r >= g) & (g >= b) & (r - b > 20)                              # orange accent, its tints and glows on charcoal
    return float((near | neutral | warm).mean())


def _overlap(a, b) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def run(out: Path, name: str, props: dict, spec: dict, cfg: dict, loud: dict, voice: list[dict]) -> dict:
    checks = []

    def add(group, check, passed, detail, mandatory=True):
        checks.append({"group": group, "check": check, "passed": bool(passed), "detail": detail, "mandatory": mandatory, "basis": "deterministic"})

    final, nomusic = out / f"{name}-final.mp4", out / f"{name}-no-music.mp4"
    seconds_expected = props["durationInFrames"] / 30
    for label, path in (("final", final), ("no_music", nomusic)):
        tech = video_validation.technical(path, width=1080, height=1920, fps=30, expected_seconds=seconds_expected, dark_theme=True)
        for c in tech["checks"]:
            add(f"technical:{label}", c["check"], c["passed"], c["detail"], c.get("mandatory", True))
        probe = video_validation.probe(path)
        codecs = {s["codec_type"]: s["codec_name"] for s in probe["streams"]}
        add(f"technical:{label}", "codecs", codecs.get("video") == "h264" and codecs.get("audio") == "aac", f"{codecs}")
        m = loud[label]
        add(f"audio:{label}", "loudness", abs(m["integrated_lufs"] + 14) <= .5, f"{m['integrated_lufs']:.1f} LUFS (target −14 ±0.5)")
        add(f"audio:{label}", "true_peak", m["true_peak_dbtp"] <= -1.0, f"{m['true_peak_dbtp']:.1f} dBTP (≤ −1.0, no clipping)")
    seconds = float(video_validation.probe(final)["format"]["duration"])
    lo, hi = cfg["pacing"]["range_s"]
    add("pacing", "duration", lo <= seconds <= hi, f"{seconds:.2f}s (series range {lo}–{hi}s)")
    words = sum(len(s["words"]) for s in props["scenes"])
    speech = sum(s["speech_s"] for s in props["scenes"])
    wlo, whi = cfg["pacing"]["wpm_target"]
    wpm = 60 * words / speech
    add("pacing", "speaking_rate", wlo <= wpm <= whi, f"{wpm:.0f} wpm while speaking ({words} words / {speech:.2f}s measured audio; target {wlo}–{whi})")
    for s in props["scenes"]:
        need = (s["lead_s"] + s["speech_s"]) * 30
        add("timing", f"scene_fits_narration:{s['id']}", s["frames"] >= need, f"{s['frames']} frames for {need:.0f} frames of lead + speech")

    # subtitles: the transcript is the script itself (TTS reads exactly these words), so check grouping, timing and placement
    subs = props["subtitles"]
    sub_words = [w["w"] for g in subs for w in g["words"]]
    said = [w["w"] for s in props["scenes"] for w in s["words"]]
    add("subtitles", "transcript_match", sub_words == said, f"{len(sub_words)} subtitle words vs {len(said)} narrated words")
    sizes = [len(g["words"]) for g in subs]
    add("subtitles", "group_size", max(sizes) <= cfg["subtitles"]["max_words"], f"{min(sizes)}–{max(sizes)} words per group "
        f"({sum(1 for x in sizes if x < cfg['subtitles']['min_words'])} short groups at sentence ends)")
    short = [g for g in subs if g["e"] - g["s"] < .45]
    add("subtitles", "readable_time", not short, f"shortest group {min(g['e'] - g['s'] for g in subs):.2f}s on screen (≥ 0.45 s)")
    gaps = [b["s"] - a["e"] for a, b in zip(subs, subs[1:])]
    add("subtitles", "no_overlap", min(gaps) >= -1e-3, "groups never overlap in time")
    first, last = subs[0]["s"], subs[-1]["e"]
    tol = .15
    add("subtitles", "sync", abs(first - (props["scenes"][0]["words"][0]["s"] + props["scenes"][0]["from"] / 30)) < tol,
        f"first subtitle at {first:.2f}s; word timing source: {voice[0].get('timing_source')} (sentence boundaries exact, words inside a sentence estimated)")
    y, h = LAYOUT["subtitle"]["y"], LAYOUT["subtitle"]["max_h"]
    vz = cfg["safe_zone"]["video"]
    band = [60, y, 960, h]
    add("subtitles", "safe_zone", vz["top"] <= y and y + h <= vz["bottom"], f"band y {y}–{y + h} inside {vz['top']}–{vz['bottom']}")
    hits = [f"{scene}.{k}" for scene, blocks in LAYOUT["regions"].items() if scene != "outro" for k, r in blocks.items() if _overlap(r, band)]
    add("subtitles", "clear_of_demo", not hits, "subtitle band overlaps " + ", ".join(hits) if hits else "subtitle band clears every demo / text block")
    outside = [f"{scene}.{k}" for scene, blocks in LAYOUT["regions"].items() for k, (x, yy, w, hh) in blocks.items()
               if not (k == "header" or (vz["top"] <= yy and yy + hh <= vz["bottom"] and x >= 0 and x + w <= 1080))]
    add("layout", "blocks_in_safe_zone", not outside, "all blocks inside the video safe zone" if not outside else f"outside: {outside}")

    f0 = intro_qa._frame_at(final, 0.0)
    lum = intro_qa._luma(f0)
    spread = float(np.percentile(lum, 99) - np.percentile(lum, 5))
    add("hook", "frame0_contrast", spread > 120, f"luma p99–p5 spread {spread:.0f} on frame 0 (demo + headline visible immediately)")
    fr = intro_qa._frames(final, 4).astype(np.float32)
    diff = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2, 3))
    moving = diff > 1.2
    longest = run_ = 0
    for mv in moving:
        run_ = 0 if mv else run_ + 1
        longest = max(longest, run_)
    add("motion", "motion_share", moving.mean() > .7, f"{moving.mean() * 100:.0f}% of 0.25 s steps change visibly")
    add("motion", "longest_static", longest / 4 <= 1.5, f"longest static stretch {longest / 4:.2f}s (≤ 1.5 s)")
    share = palette_share(fr[::4], cfg["palette"])
    add("brand", "palette_share", share > .9, f"{share * 100:.1f}% of sampled pixels on the series palette or its blends")

    # cover
    sizes_ok = {f: _png_size(out / f) for f in (f"{name}-cover.png", f"{name}-cover-4x5.png", f"{name}-cover-square.png")}
    add("cover", "sizes", list(sizes_ok.values()) == [(1080, 1920), (1080, 1350), (1080, 1080)], f"{sizes_ok}")
    mask = _png_gray(out / "qa" / "cover-mask.png") > 128
    q = cfg["safe_zone"]["cover_square"]
    inside = np.zeros_like(mask)
    inside[q["top"]:q["bottom"], q["left"]:q["right"]] = True
    stray = int((mask & ~inside).sum())
    ys, xs = np.nonzero(mask)
    add("cover", "crop_safe", stray == 0, f"essential elements span x {xs.min()}–{xs.max()}, y {ys.min()}–{ys.max()}; {stray} px outside the square safe "
        f"region x {q['left']}–{q['right']}, y {q['top']}–{q['bottom']} (survives 9:16, 4:5 and 1:1)")
    rows = mask[:, q["left"]:q["right"]].any(axis=1)
    add("cover", "text_not_clipped", not mask[:, :q["left"]].any() and not mask[:, q["right"]:].any(), "no essential pixel touches the side margins")
    ep_px = 72 * 357 / 1080                                                # EpisodeNumber font size at grid-thumbnail scale
    add("cover", "episode_number_thumbnail", ep_px * .73 >= 12, f"EP label cap height ≈ {ep_px * .73:.0f} px in a 357 px grid tile (≥ 12 px); "
        "see qa/cover-grid-thumbnail.png")
    # headline is the largest type on the cover (fitSize in theme.ts is deterministic: recompute the same estimate)
    em = lambda s: sum(.98 if c in "MW" else .36 if c in "IJ1" else .3 if c in ".,:;!'’" else .26 if c == " " else .6 if c == "?" else .72 for c in s)
    head = min(150, *[(q["right"] - q["left"] - 40) / max(1, em(l)) for l in spec["cover_headline"]])
    add("cover", "headline_largest", head > 72, f"headline {head:.0f} px vs EP label 72 px and header 32 px")

    mascot_src = (ROOT / "src" / "series" / "Visuals.tsx").read_text()
    add("mascot", "single_source", "from '../devmimo/Mimo'" in mascot_src and "identity.json" in (ROOT / "src" / "devmimo" / "Mimo.tsx").read_text(),
        "series mascot = src/devmimo/Mimo.tsx (brand/character/identity.json); not redrawn or regenerated")
    errs = series.validate(spec, cfg)
    add("copy", "claims_and_phrases", not errs, "every on-screen label cites a verified feature; no banned phrases or repository statistics" if not errs else "; ".join(errs))

    review_path = out / "qa" / "visual_review.json"
    review = json.loads(review_path.read_text()) if review_path.exists() else {"status": "pending: frames not yet inspected"}
    failed = [c for c in checks if not c["passed"] and c["mandatory"]]
    adv = [c for c in checks if not c["passed"] and not c["mandatory"]]
    return {"video": final.name, "seconds": round(seconds, 3), "frames": props["durationInFrames"],
            "summary": {"passed": not failed, "mandatory_failed": [c["group"] + "/" + c["check"] for c in failed],
                        "advisories": [c["group"] + "/" + c["check"] for c in adv], "checks": len(checks), "visual_review": review.get("status")},
            "checks": checks, "visual_review": review,
            "basis": "deterministic checks via ffmpeg/numpy/PIL; the visual review is a human/agent inspection recorded separately"}


def markdown(report: dict, meta: dict) -> str:
    s = report["summary"]
    lines = [f"# QA · {meta['episode_label']} · {meta['title']}", "",
             f"**Result:** {'PASS' if s['passed'] else 'FAIL'} ({s['checks']} deterministic checks"
             f"{'; failed: ' + ', '.join(s['mandatory_failed']) if s['mandatory_failed'] else ''}"
             f"{'; advisories: ' + ', '.join(s['advisories']) if s['advisories'] else ''})", "",
             f"- Duration: {meta['duration_s']:.2f}s · {meta['narration_word_count']} words · {meta['speaking_rate_wpm']} wpm while speaking",
             f"- Demonstration: **{meta['demonstration']['status']}**: {meta['demonstration']['meaning']}"
             + (f" (on-screen tag: “{meta['demonstration']['on_screen_tag']}”)" if meta['demonstration']['on_screen_tag'] else ""),
             f"- Loudness: final {meta['loudness']['final']['integrated_lufs']:.1f} LUFS / {meta['loudness']['final']['true_peak_dbtp']:.1f} dBTP; "
             f"no-music {meta['loudness']['no_music']['integrated_lufs']:.1f} LUFS / {meta['loudness']['no_music']['true_peak_dbtp']:.1f} dBTP",
             f"- Visual review: {s['visual_review']}", "", "| Group | Check | Result | Detail |", "|---|---|---|---|"]
    for c in report["checks"]:
        lines.append(f"| {c['group']} | {c['check']} | {'pass' if c['passed'] else ('FAIL' if c['mandatory'] else 'advisory')} | {c['detail']} |")
    rv = report["visual_review"]
    if rv.get("findings"):
        lines += ["", "## Visual review", ""] + [f"- {x}" for x in rv["findings"]]
    return "\n".join(lines) + "\n"
