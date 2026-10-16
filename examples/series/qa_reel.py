"""QA for a reel-format (v2) episode. Reuses the episode QA helpers (technical probe, loudness, frame metrics, palette, cover mask) and
adds the reel rules: every block inside the Instagram safe area (series.json safe_zone.reel_v2), subtitles above the caption UI, the
premise readable on frame 0, no black frames, a short ending (no branded outro), hook variants 3–5.5 s, and the two-projects rule
(the Adobe-style recreations are labelled as such and never presented as made with the featured tool).

The visual review is a separate, labelled record (qa/visual_review.json) written by whoever inspected the frames.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "examples" / "devmimo"))
sys.path.insert(0, str(HERE))
import qa as intro_qa  # noqa: E402
import qa_episode as qe  # noqa: E402
from video_mcp import series  # noqa: E402
from video_mcp.quality import video_validation  # noqa: E402

LAYOUT = json.loads((ROOT / "src" / "series" / "layout-reel.json").read_text())


def black_frames(path: Path) -> list[str]:
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(path), "-vf", "blackdetect=d=0.05:pix_th=0.06", "-an", "-f", "null", "-"],
                       capture_output=True, text=True, timeout=600)
    return re.findall(r"black_start:\S+ black_end:\S+", r.stderr)


def run(out: Path, name: str, props: dict, spec: dict, cfg: dict, loud: dict, voice: list[dict], hooks: list[dict]) -> dict:
    checks = []

    def add(group, check, passed, detail, mandatory=True):
        checks.append({"group": group, "check": check, "passed": bool(passed), "detail": detail, "mandatory": mandatory, "basis": "deterministic"})

    final, nomusic = out / f"{name}-final.mp4", out / f"{name}-no-music.mp4"
    expected = props["durationInFrames"] / 30
    for label, path in (("final", final), ("no_music", nomusic)):
        tech = video_validation.technical(path, width=1080, height=1920, fps=30, expected_seconds=expected, dark_theme=True)
        for c in tech["checks"]:
            add(f"technical:{label}", c["check"], c["passed"], c["detail"], c.get("mandatory", True))
        probe = video_validation.probe(path)
        v = next(s for s in probe["streams"] if s["codec_type"] == "video")
        codecs = {s["codec_type"]: s["codec_name"] for s in probe["streams"]}
        add(f"technical:{label}", "exact_1080x1920", (v["width"], v["height"]) == (1080, 1920), f"{v['width']}x{v['height']}")
        add(f"technical:{label}", "codecs", codecs.get("video") == "h264" and codecs.get("audio") == "aac", f"{codecs}")
        m = loud[label]
        add(f"audio:{label}", "loudness", abs(m["integrated_lufs"] + 14) <= .5, f"{m['integrated_lufs']:.1f} LUFS (target −14 ±0.5)")
        add(f"audio:{label}", "true_peak", m["true_peak_dbtp"] <= -1.0, f"{m['true_peak_dbtp']:.1f} dBTP (≤ −1.0, no clipping)")
        blacks = black_frames(path)
        add(f"technical:{label}", "no_black_frames", not blacks, "no black frames (blackdetect ≥ 0.05 s)" if not blacks else "; ".join(blacks))

    seconds = float(video_validation.probe(final)["format"]["duration"])
    lo, hi = cfg["pacing"]["range_s"]
    add("pacing", "duration", lo <= seconds <= hi, f"{seconds:.2f}s (episode range {lo}–{hi}s; brief arc ≈ 31 s)")
    scenes = props["scenes"]
    words = sum(len(s["words"]) for s in scenes)
    speech = sum(s["speech_s"] for s in scenes)
    wlo, whi = cfg["pacing"]["wpm_target"]
    wpm = 60 * words / speech
    add("pacing", "speaking_rate", wlo <= wpm <= whi, f"{wpm:.0f} wpm while speaking ({words} words / {speech:.2f}s; target {wlo}–{whi})")
    for s in scenes:
        need = (s["lead_s"] + s["speech_s"]) * 30
        add("timing", f"beat_fits_narration:{s['id']}", s["frames"] >= need, f"{s['frames']} frames for {need:.0f} frames of lead + speech")
    gaps = [(s["id"], s["frames"] / 30 - s["lead_s"] - s["speech_s"]) for s in scenes]
    longest = max(gaps, key=lambda g: g[1])
    add("timing", "no_awkward_pauses", longest[1] <= 1.6, f"longest silence after a beat's narration: {longest[1]:.2f}s ({longest[0]}; ≤ 1.6 s)")
    last = scenes[-1]
    tail = last["frames"] / 30 - (last["words"][-1]["e"] if last["words"] else 0)
    add("ending", "ends_on_question", tail <= 1.0 and last["kind"] == "question", f"reel ends {tail:.2f}s after the last word of the question beat; no outro")

    subs = props["subtitles"]
    add("subtitles", "transcript_match", [w["w"] for g in subs for w in g["words"]] == [w["w"] for s in scenes for w in s["words"]], "subtitle words = narrated words")
    sizes = [len(g["words"]) for g in subs]
    add("subtitles", "group_size", max(sizes) <= cfg["subtitles"]["max_words"], f"{min(sizes)}–{max(sizes)} words per group")
    add("subtitles", "readable_time", min(g["e"] - g["s"] for g in subs) >= .45, f"shortest group {min(g['e'] - g['s'] for g in subs):.2f}s on screen (≥ 0.45 s)")
    add("subtitles", "no_overlap", min((b["s"] - a["e"] for a, b in zip(subs, subs[1:])), default=0) >= -1e-3, "groups never overlap in time")
    first = scenes[0]["words"][0]["s"] + scenes[0]["from"] / 30
    add("subtitles", "sync", abs(subs[0]["s"] - first) < .15, f"first subtitle at {subs[0]['s']:.2f}s, first word at {first:.2f}s; timing source {voice[0].get('timing_source')}")
    emph = {w["w"] for g in subs for w in g["words"] if w["em"]}
    add("subtitles", "emphasis", len(emph) >= 4, f"orange words: {', '.join(sorted(emph))}")
    sb = LAYOUT["subtitle"]
    safe = LAYOUT["safe"]
    band = [sb["x"], sb["y"], sb["w"], sb["max_h"]]
    add("subtitles", "above_caption_ui", sb["y"] + sb["max_h"] <= safe["bottom"] and sb["x"] >= safe["left"] and sb["x"] + sb["w"] <= safe["right"],
        f"band x {sb['x']}–{sb['x'] + sb['w']}, y {sb['y']}–{sb['y'] + sb['max_h']} inside safe x {safe['left']}–{safe['right']}, y ≤ {safe['bottom']}")
    hits = [f"{b}.{k}" for b, blocks in LAYOUT["regions"].items() for k, r in blocks.items() if qe._overlap(r, band)]
    add("subtitles", "clear_of_content", not hits, "subtitle band clears every content block" if not hits else "overlaps " + ", ".join(hits))

    # layout: every block inside the Instagram safe area (configurable margins in series.json)
    m = cfg["safe_zone"]["reel_v2"]
    add("layout", "safe_area_matches_config", (safe["left"], safe["top"], 1080 - safe["right"], 1920 - safe["bottom"]) == (m["left"], m["top"], m["right"], m["bottom"]),
        f"layout safe area x {safe['left']}–{safe['right']}, y {safe['top']}–{safe['bottom']} = margins top {m['top']}, bottom {m['bottom']}, left {m['left']}, right {m['right']}")
    outside = [f"{b}.{k}" for b, blocks in LAYOUT["regions"].items() for k, (x, y, w, h) in blocks.items()
               if not (safe["left"] <= x and x + w <= safe["right"] and safe["top"] <= y and y + h <= safe["bottom"])]
    x, y, w, h = LAYOUT["bug"]
    if not (safe["left"] <= x and x + w <= safe["right"] and safe["top"] <= y and y + h <= safe["bottom"]):
        outside.append("bug")
    add("layout", "blocks_in_safe_area", not outside, "header, hook, demo, repository, subtitles and CTA blocks inside the safe area" if not outside else f"outside: {outside}")
    add("layout", "instagram_previews", (out / "qa" / "instagram-safe-preview.png").exists(), "qa/instagram-safe-preview.png and qa/instagram/*.png (simulated Reels UI)")

    # hook: frame 0 already carries a real result + the premise
    shock = scenes[0]
    add("hook", "starts_with_result", shock["kind"] == "shock" and bool(shock.get("shots")), "frame 0 shows a real recreation screenshot (no logo, title card or fade)")
    add("hook", "premise_on_frame0", (shock.get("headline_at") or [""])[0] == "", f"“{shock.get('headline', [''])[0]}” is on screen from frame 0; "
        f"“{(shock.get('headline') or ['', ''])[-1]}” lands with the narration")
    f0 = intro_qa._frame_at(final, 0.0)
    lum = intro_qa._luma(f0)
    spread = float(np.percentile(lum, 99) - np.percentile(lum, 5))
    add("hook", "frame0_contrast", spread > 120, f"luma p99–p5 spread {spread:.0f} on frame 0")
    for h in hooks:
        add("hook", f"variant_{h['id']}", 3.0 <= h["seconds"] <= 5.5 and (out / h["file"]).exists(), f"{h['file']}: {h['seconds']:.2f}s, “{h['narration']}”")

    fr = intro_qa._frames(final, 4).astype(np.float32)
    diff = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2, 3))
    moving = diff > 1.2
    longest_run = run_ = 0
    for mv in moving:
        run_ = 0 if mv else run_ + 1
        longest_run = max(longest_run, run_)
    add("motion", "motion_share", moving.mean() > .7, f"{moving.mean() * 100:.0f}% of 0.25 s steps change visibly")
    add("motion", "longest_static", longest_run / 4 <= 1.5, f"longest static stretch {longest_run / 4:.2f}s (≤ 1.5 s)")
    share = qe.palette_share(fr[::4], cfg["palette"])
    add("brand", "palette_share", share > .75, f"{share * 100:.1f}% of sampled pixels on the series palette (third-party screenshots are shown as they are)",
        mandatory=False)

    # cover (same template as EP. 001)
    sizes = {f: qe._png_size(out / f) for f in (f"{name}-cover.png", f"{name}-cover-4x5.png", f"{name}-cover-square.png")}
    add("cover", "sizes", list(sizes.values()) == [(1080, 1920), (1080, 1350), (1080, 1080)], f"{sizes}")
    mask = qe._png_gray(out / "qa" / "cover-mask.png") > 128
    q = cfg["safe_zone"]["cover_square"]
    inside = np.zeros_like(mask)
    inside[q["top"]:q["bottom"], q["left"]:q["right"]] = True
    stray = int((mask & ~inside).sum())
    add("cover", "crop_safe", stray == 0, f"{stray} essential px outside the square safe region (survives 9:16, 4:5 and 1:1)")
    n_frames = len(spec.get("project_visual_assets", {}).get("frames", []))
    add("cover", "few_large_previews", 2 <= n_frames <= 3, f"{n_frames} interface previews (2–3, not seven tiny ones)")
    em = lambda s: sum(.98 if c in "MW" else .36 if c in "IJ1" else .3 if c in ".,:;!'’" else .26 if c == " " else .6 if c == "?" else .72 for c in s)
    head = min(150, *[(q["right"] - q["left"] - 40) / max(1, em(line)) for line in spec["cover_headline"]])
    add("cover", "headline_thumbnail", head * 357 / 1080 >= 28, f"headline {head:.0f} px → {head * 357 / 1080:.0f} px in a 357 px grid tile (≥ 28)")

    # claims and the two-projects rule
    errs = series.validate(spec, cfg)
    add("copy", "claims_and_phrases", not errs, "every on-screen claim cites a verified feature; no banned phrases or repository statistics" if not errs else "; ".join(errs))
    shock_text = " ".join(next(b for b in spec["beats"] if b["id"] == "shock").get("text", [])).upper()
    add("copy", "recreations_labelled", "NOT ADOBE" in shock_text and all(s.get("inspired") for s in shock.get("shots", [])),
        "every recreation is named and tagged “-style · open source”; hook tag: " + shock_text)
    notes = " ".join(spec["demo"].get("notes", [])).lower()
    add("copy", "projects_kept_separate", "not used on artcraft" in notes and "a different project" in " ".join(
        next(b for b in spec["beats"] if b["id"] == "discovery").get("text", [])).lower(), "REA card says A DIFFERENT PROJECT; metadata states REA was not used on ArtCraft or Adobe")
    statuses = {f["id"]: f["status"] for f in spec["verified_features"]}
    add("copy", "proof_is_real_run", all(statuses.get(k) == "verified-run" for k in ("mcp_agents", "no_source", "observe", "inspect", "rebuild")),
        "proof + possibility claims come from the captured REA run (evidence/episode-002-rea)")
    mascot = (ROOT / "src" / "series" / "Visuals.tsx").read_text()
    add("mascot", "single_source", "from '../devmimo/Mimo'" in mascot, "Mimo = src/devmimo/Mimo.tsx (brand/character/identity.json); unchanged")

    review_path = out / "qa" / "visual_review.json"
    review = json.loads(review_path.read_text()) if review_path.exists() else {"status": "pending: frames not yet inspected"}
    failed = [c for c in checks if not c["passed"] and c["mandatory"]]
    adv = [c for c in checks if not c["passed"] and not c["mandatory"]]
    return {"video": final.name, "seconds": round(seconds, 3), "frames": props["durationInFrames"],
            "summary": {"passed": not failed, "mandatory_failed": [c["group"] + "/" + c["check"] for c in failed],
                        "advisories": [c["group"] + "/" + c["check"] for c in adv], "checks": len(checks), "visual_review": review.get("status")},
            "checks": checks, "visual_review": review}


def markdown(report: dict, meta: dict) -> str:
    s = report["summary"]
    lines = [f"# QA · {meta['episode_label']} · {meta['title']}", "",
             f"**Result:** {'PASS' if s['passed'] else 'FAIL'} ({s['checks']} deterministic checks"
             f"{'; failed: ' + ', '.join(s['mandatory_failed']) if s['mandatory_failed'] else ''}"
             f"{'; advisories: ' + ', '.join(s['advisories']) if s['advisories'] else ''})", "",
             f"- Duration: {meta['duration_s']:.2f}s · {meta['narration_word_count']} words · {meta['speaking_rate_wpm']} wpm while speaking",
             f"- Demonstration: **{meta['demonstration']['status']}**: {meta['demonstration']['meaning']}",
             f"- Loudness: final {meta['loudness']['final']['integrated_lufs']:.1f} LUFS / {meta['loudness']['final']['true_peak_dbtp']:.1f} dBTP; "
             f"no-music {meta['loudness']['no_music']['integrated_lufs']:.1f} LUFS / {meta['loudness']['no_music']['true_peak_dbtp']:.1f} dBTP",
             f"- Instagram safe area: top {meta['safe_zone']['top']}, bottom {meta['safe_zone']['bottom']}, left {meta['safe_zone']['left']}, "
             f"right {meta['safe_zone']['right']} px (previews: qa/instagram-safe-preview.png)",
             f"- Visual review: {s['visual_review']}", "", "| Group | Check | Result | Detail |", "|---|---|---|---|"]
    for c in report["checks"]:
        lines.append(f"| {c['group']} | {c['check']} | {'pass' if c['passed'] else ('FAIL' if c['mandatory'] else 'advisory')} | {c['detail']} |")
    rv = report["visual_review"]
    for key, title in (("brief_checklist", "Brief checklist (visual review)"), ("findings", "Visual review findings"), ("hook_choice", "Hook choice")):
        if rv.get(key):
            lines += ["", f"## {title}", ""]
            items = rv[key]
            if isinstance(items, dict):
                lines += [f"- **{k}**: {v}" for k, v in items.items()]
            else:
                lines += [f"- {x}" for x in items]
    return "\n".join(lines) + "\n"
