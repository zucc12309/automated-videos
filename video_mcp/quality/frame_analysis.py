"""Visual QA.

Deterministic layout checks use the render metadata (props.json) and the shared design tokens (src/studio/themes.json):
safe areas, caption band, text capacity vs. clamping limits, font sizes, theme contrast, layout repetition, presenter
placement. Pixel heuristics on sampled frames catch blank stages and identical frames. OCR is not used.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SAFE = {"left": 120, "right": 960, "top": 290, "bottom": 1248}
STAGE = {"left": 120, "top": 360, "width": 840, "height": 700}
MIN_BODY_PX, MIN_LABEL_PX = 36, 26          # phone legibility at 1080 px width (V2.1: raised after review)
TEXT_FORWARD = {"heroWord", "quote", "hookStack", "loop", "mascotCloseup", "hookBold", "outroCTA"}

# (field, clamp limit in chars, font px) mirrored from the TSX components.
LAYOUT_TEXT = {
    "heroWord": [("focus", 22, 96)], "quote": [("text", 120, 64)], "listStack": [("heading", 34, 64), ("points", 26, 48)],
    "steps": [("points", 22, 52)], "compare": [("points", 40, 50)], "repoCard": [("label", 18, 64)], "chips": [("points", 20, 46)],
    "deviceMock": [("heading", 26, 46), ("points", 20, 38)], "chat": [("heading", 44, 42), ("points", 28, 44)],
    "nodeGraph": [("points", 16, 40), ("focus", 14, 52)], "hookBold": [("heading", 46, 104)], "readmeScroll": [("label", 30, 42)],
    "repoConnect": [("points", 14, 40)], "outroCTA": [("heading", 34, 96)], "hookStack": [("heading", 40, 84)], "docStamp": [("heading", 40, 60), ("points", 34, 40)],
    "recap": [("label", 22, 52)], "codeBlock": [("heading", 30, 52), ("code", 48, 38)], "flowDiagram": [("nodes", 26, 46)],
    "timeline": [("timeline", 26, 46)], "chartBars": [("heading", 30, 50)], "browserMock": [("heading", 32, 54), ("points", 30, 42)],
    "warningCard": [("heading", 48, 70), ("points", 38, 44)], "splitCompare": [("compare", 30, 42)], "cinematic": [("heading", 40, 76)],
    "terminal": [("points", 32, 40)], "bigNumber": [("focus", 12, 200)], "starMeter": [("label", 18, 44)], "mascotCloseup": [("focus", 30, 60)],
}


def themes() -> dict:
    return json.loads((ROOT / "src/studio/themes.json").read_text())


def _lum(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4
    return .2126 * f(r) + .7152 * f(g) + .0722 * f(b)


def contrast(a: str, b: str) -> float:
    hi, lo = sorted([_lum(a), _lum(b)], reverse=True)
    return round((hi + .05) / (lo + .05), 2)


def _texts(layout: str, field: str, scene: dict, beat: dict) -> list[str]:
    vd = scene.get("visualData") or {}
    if field == "points":
        return scene.get("points") or []
    if field == "focus":
        return [beat.get("focus", "")]
    if field in ("heading", "label"):
        return [scene.get(field) or ""]
    if field == "text":
        return [beat.get("text", "")]
    if field == "code":
        return vd.get("code") or []
    if field in ("nodes", "timeline"):
        return vd.get(field) or vd.get("steps") or scene.get("points") or []
    if field == "compare":
        return (vd.get("compare_left") or []) + (vd.get("compare_right") or [])
    return []


def layout_checks(props: dict) -> dict:
    issues, checks = [], []
    variant = props.get("variant", {})
    theme_name = variant.get("theme") or props.get("theme")
    palette = themes().get(theme_name) if theme_name else None

    def add(name, passed, detail, scene=None, mandatory=False, kind="layout", **extra):
        row = {"check": name, "passed": bool(passed), "detail": detail, "scene": scene, "mandatory": mandatory, "basis": "deterministic", "kind": kind, **extra}
        checks.append(row)
        if not passed:
            issues.append(row)

    add("stage_inside_safe_area", STAGE["left"] >= SAFE["left"] and STAGE["left"] + STAGE["width"] <= SAFE["right"]
        and STAGE["top"] >= SAFE["top"] and STAGE["top"] + STAGE["height"] <= SAFE["bottom"], f"stage {STAGE} within {SAFE}", mandatory=True)
    if palette:
        for role, minimum in (("ink", 4.5), ("muted", 4.5), ("accent", 3.0)):
            ratio = contrast(palette[role], palette["bg"])
            add(f"contrast_{role}", ratio >= minimum, f"{theme_name} {role}/bg {ratio}:1 (min {minimum})", kind="contrast")
        add("contrast_surface", contrast(palette["ink"], palette["surface"]) >= 4.5, f"ink/surface {contrast(palette['ink'], palette['surface'])}:1", kind="contrast")
    order = []
    for scene in props["scenes"]:
        sid = scene.get("id") or f"scene_{props['scenes'].index(scene) + 1:03d}"
        for beat in scene.get("beats", []):
            layout = beat.get("layout", "")
            order.append(layout)
            for field, limit, px in LAYOUT_TEXT.get(layout, []):
                for text in _texts(layout, field, scene, beat):
                    if len(text) > limit:
                        add("text_fits", False, f"{layout}.{field} '{text[:40]}' is {len(text)} chars > {limit} (will be clipped)", sid, kind="overflow",
                            field=field, limit=limit, layout=layout)
                if px < (MIN_LABEL_PX if field in ("label",) else MIN_BODY_PX):
                    add("font_size", False, f"{layout}.{field} {px}px below minimum", sid, kind="tiny_text")
            if layout == "codeBlock":
                longest = max((len(x) for x in (scene.get("visualData") or {}).get("code") or [""]), default=0)
                font = min(40, 720 / (.6 * max(1, longest)))
                add("code_font_size", font >= 28, f"longest line {longest} chars -> {font:.0f}px", sid, kind="tiny_text")
            if beat.get("anchor") == "center" and layout not in ("mascotCloseup",) and scene.get("character", True):
                add("presenter_occlusion", False, f"presenter centred over {layout}", sid, kind="occlusion")
            items = sum(1 for x in props["scenes"] if x.get("item", 0) > 0)
            if layout in ("hookStack", "recap") and items < 2:
                add("layout_has_data", False, f"{layout} needs numbered items; video has {items}", sid, kind="blank")
            if layout in ("repoCard", "starMeter") and not props.get("repos"):
                add("layout_has_data", False, f"{layout} without repository data", sid, kind="blank")
            if layout == "cinematic" and not scene.get("media"):
                add("asset_present", False, "cinematic layout without footage", sid, mandatory=True, kind="missing_asset")
        words = scene.get("words") or []
        longest_chunk = max((sum(len(w["w"]) + 1 for w in words[i:i + 4]) for i in range(0, max(1, len(words)), 4)), default=0)
        caption_lines = 1 + int(longest_chunk * .55 * 70 / (SAFE["right"] - SAFE["left"]))
        add("caption_band", caption_lines <= 2, f"longest caption chunk ~{caption_lines} line(s)", sid, kind="caption")
    repeats = sum(1 for a, b in zip(order, order[1:]) if a == b)
    add("no_back_to_back_layouts", repeats == 0, f"{repeats} repeat(s)", kind="repetition")
    distinct = len(set(order))
    add("layout_variety", distinct >= min(5, max(1, len(order) // 2)), f"{distinct} distinct layouts over {len(order)} beats", kind="repetition")
    add("single_theme", bool(theme_name) or bool(variant.get("palette")), f"theme={theme_name or variant.get('palette')}", kind="consistency")
    return {"checks": checks, "issues": issues, "layout_order": order}


def sample_times(props: dict) -> list[tuple[float, str, str]]:
    fps = props["fps"]
    out = [(0.0, "first_frame", "")]
    for i, s in enumerate(props["scenes"]):
        sid = s.get("id") or f"scene_{i + 1:03d}"
        start, end = s["from"] / fps, (s["from"] + s["frames"]) / fps
        out += [(start + .15, "scene_entrance", sid), ((start + end) / 2, "scene_mid", sid), (max(start, end - .2), "scene_exit", sid)]
        for b in s.get("beats", [])[1:]:
            out.append((start + b["s"] + .1, "beat_boundary", sid))
    total = props["durationInFrames"] / fps
    out.append((max(0, total - .1), "final_frame", ""))
    seen, uniq = set(), []
    for t, kind, sid in sorted(out):
        key = round(t, 1)
        if key not in seen:
            seen.add(key)
            uniq.append((round(t, 3), kind, sid))
    return uniq[:60]


def grab(video: Path, t: float, w=270, h=480) -> np.ndarray | None:
    out = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-vf", f"scale={w}:{h}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, timeout=60)
    if out.returncode or len(out.stdout) != w * h * 3:
        return None
    return np.frombuffer(out.stdout, dtype=np.uint8).reshape(h, w, 3)


def frame_checks(video: Path, props: dict, qa_dir: Path) -> dict:
    frames_dir = qa_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    rows, issues = [], []
    stage = (slice(int(360 / 4), int(1060 / 4)), slice(int(120 / 4), int(960 / 4)))
    previous_mid = None
    for n, (t, kind, sid) in enumerate(sample_times(props)):
        img = grab(video, t)
        if img is None:
            issues.append({"check": "frame_decode", "scene": sid, "detail": f"could not decode frame at {t}s", "basis": "deterministic", "kind": "decode"})
            continue
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-vf", "scale=216:384",
                        str(frames_dir / f"{n:03d}.jpg")], timeout=60)
        luma = img.mean(axis=2)
        stage_std = float(luma[stage].std())
        row = {"t": t, "kind": kind, "scene": sid, "mean_luma": round(float(luma.mean()), 1), "stage_std": round(stage_std, 2)}
        rows.append(row)
        if kind == "scene_mid" and stage_std < 4:
            issues.append({"check": "stage_has_content", "scene": sid, "detail": f"stage nearly uniform at {t:.2f}s (std {stage_std:.1f})",
                           "basis": "heuristic", "kind": "blank"})
        if kind == "scene_mid":
            if previous_mid is not None and float(np.abs(previous_mid.astype(int) - img.astype(int)).mean()) < 1.5:
                issues.append({"check": "distinct_scenes", "scene": sid, "detail": "mid-frame nearly identical to previous scene",
                               "basis": "heuristic", "kind": "repetition"})
            previous_mid = img
    sheet = qa_dir / "contact_sheet.jpg"
    count = len(list(frames_dir.glob("*.jpg")))
    if count:
        cols = 8
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "1", "-i", str(frames_dir / "%03d.jpg"),
                        "-vf", f"tile={cols}x{(count + cols - 1) // cols}:padding=6:margin=6:color=0x202020", "-frames:v", "1", str(sheet)], timeout=120)
    return {"samples": rows, "issues": issues, "contact_sheet": str(sheet) if sheet.exists() else None}
