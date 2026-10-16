"""Build a reel-format (v2) episode: number → narration → timing → subtitles → sound → render → hook variants → covers →
Instagram-overlay previews → QA → metadata. Same series system and audio/render pieces as build_episode.py (Kokoro narration with
the wpm search, true-peak master, cover template, crops); only the story structure and the layout differ.

    .venv/bin/python examples/series/build_reel.py series/mimo-found-this-on-github/specs/morluto-rea.json
    .venv/bin/python examples/series/build_reel.py SPEC --reuse-voice          # keep cached narration
    .venv/bin/python examples/series/build_reel.py SPEC --validate-only

The spec sets "format": "reel-v2" and lists seven beats (shock, context, mystery, discovery, proof, possibility, question), each with
its narration and on-screen data, plus `hook_variants` (3–5 s previews of alternative openings, same verified facts).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "examples" / "devmimo"))
sys.path.insert(0, str(HERE))

import build_intro as bi  # noqa: E402
import build_episode as be  # noqa: E402  (fit_voice, master_tp, fetch_media, cover_crops, grid_preview)
from video_mcp import audio as fx, series, settings  # noqa: E402
from video_mcp.audio import RATE  # noqa: E402

FPS = bi.FPS
LAYOUT = json.loads((ROOT / "src" / "series" / "layout-reel.json").read_text())
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
BEAT_KEYS = ("id", "narration", "lead_s", "min_tail_s", "hold")


def media_refs(spec: dict) -> list[str]:
    """Every image / video path (under public/) the reel or its cover shows."""
    refs = []

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in ("src", "input", "output") and isinstance(v, str) and "/" in v:
                    refs.append(v)
                else:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(spec.get("beats", []))
    walk(spec.get("hook_variants", []))
    for v in spec.get("project_visual_assets", {}).values():
        refs += v if isinstance(v, list) else [v]
    return sorted(set(refs))


def merged_cfg(spec: dict, cfg: dict) -> dict:
    """Series config with the episode's pacing overrides (target, range, wpm) applied."""
    return {**cfg, "pacing": {**cfg["pacing"], **spec.get("pacing", {})}}


def storyboard(spec: dict, cfg: dict) -> dict:
    pacing = cfg["pacing"]
    scenes = [{"id": b["id"], "kind": b["id"], "narration": b["narration"], "lead_s": b.get("lead_s", .1), "min_tail_s": b.get("min_tail_s", .25),
               "hold": b.get("hold", 1)} for b in spec["beats"]]
    return {"scenes": scenes, "voice_speed": pacing["voice_speed"], "pacing": {"target_s": pacing["target_s"], "wpm_target": pacing["wpm_target"]}}


# ---------------------------------------------------------------- cue frames (same lookups as src/series/Reel.tsx atWord)
def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def at_word(scene: dict, token: str | None, fallback: int = 0) -> int:
    if not token:
        return fallback
    for w in scene["words"]:
        if _norm(w["w"]).startswith(_norm(token)):
            return round(w["s"] * FPS)
    return fallback


def cues(scenes: list[dict]) -> list[dict]:
    by = {s["id"]: s for s in scenes}
    out = []

    def add(sid, frame, sound, gain):
        if sid in by:
            out.append({"scene": sid, "frame": max(0, int(frame)), "sound": sound, "gain": gain})
    s = by.get("shock")
    if s:
        add("shock", 0, "tick", .55)
        add("shock", 0, "boom", .3)
        for shot in s.get("shots", [])[1:]:
            add("shock", at_word(s, shot.get("at"), s["frames"] // 2), "whoosh", .35)
        for i, tok in enumerate(s.get("headline_at", [])[1:], 1):
            add("shock", at_word(s, tok, round(s["frames"] * .55)), "pop", .5)
    c = by.get("context")
    if c:
        for i, a in enumerate(c.get("apps", [])):
            f = at_word(c, a["at"], round(c["frames"] * i / max(1, len(c["apps"]))))
            add("context", f, "whoosh" if i else "tick", .3 if i else .45)
            if i:
                add("context", f + 2, "tick", .35)
    m = by.get("mystery")
    if m:
        for i in range(0, 9, 3):
            add("mystery", i * 2, "pop", .2)
        last = m["words"][-1] if m["words"] else None
        turn = min(round(last["e"] * FPS) + 4, m["frames"] - 22) if last else round(m["frames"] * .6)
        add("mystery", turn, "glitch", .45)                                   # the story turns: brief accent, not a sting
        add("mystery", turn, "boom", .2)
    d = by.get("discovery")
    if d:
        add("discovery", 0, "whoosh", .4)
        add("discovery", 4, "pop", .35)
        add("discovery", 14, "tick", .4)
        add("discovery", 20, "tick", .35)
    p = by.get("proof")
    if p:
        add("proof", 8, "pop", .3)
        for i, st in enumerate(p.get("steps", [])):
            f = at_word(p, st["at"], round(p["frames"] * (.2 + .2 * i)))
            add("proof", f, "plug" if i == 0 else "tick", .4)
            if st["kind"] == "findings":
                add("proof", f + 6, "chime", .25)
        if p.get("stamp"):
            add("proof", at_word(p, p["stamp"].get("at"), round(p["frames"] * .7)), "stamp", .5)
    q = by.get("possibility")
    if q:
        stages = q.get("stages", [])
        ats = [at_word(q, st["at"], round(q["frames"] * (.1 + .25 * i))) for i, st in enumerate(stages)]
        for f in ats:
            add("possibility", f, "tick", .45)
        rb = ats[-1] if ats else round(q["frames"] * .6)
        add("possibility", rb, "whoosh", .3)
        add("possibility", rb + 12, "chime", .35)
        add("possibility", max(rb + 26, q["frames"] - 30), "stamp", .45)
    z = by.get("question")
    if z:
        add("question", 0, "pop", .3)
        add("question", at_word(z, z.get("question_at"), round(z["frames"] * .4)), "pop", .45)
        add("question", min(z["frames"] - 16, at_word(z, "engineer", z["frames"] - 20)), "tick", .4)
    return out


# ---------------------------------------------------------------- props
def beat_scenes(spec: dict, timed: list[dict]) -> list[dict]:
    beats = {b["id"]: b for b in spec["beats"]}
    return [{**s, **{k: v for k, v in beats[s["id"]].items() if k not in BEAT_KEYS and k != "claims"}, "narration": beats[s["id"]]["narration"]}
            for s in timed]


def reel_props(spec: dict, cfg: dict, rec: dict, scenes: list[dict], subs: list[dict], mouth: list[float]) -> dict:
    owner, name = series.normalize_repo(spec["repository"]).split("/")
    rc = spec["repo_card"]
    return {
        "fps": FPS, "durationInFrames": sum(s["frames"] for s in scenes),
        "series": {k: cfg[k] for k in ("header", "tagline", "footer", "handle", "collection")},
        "episode": {"n": rec["episode"], "label": series.fmt(rec["episode"]), "title": spec["title"], "repo": f"{owner}/{name}",
                    "category": spec.get("category", "Open source"), "headline": spec["cover_headline"], "expression": spec.get("mascot_expression", "curious"),
                    "visual": spec.get("project_visual", "terminal"), "demoStatus": spec["demo"]["status"], "demoTag": spec["demo"].get("tag"),
                    "visualAssets": spec.get("project_visual_assets", {})},
        "scenes": scenes, "subtitles": subs, "mouth": mouth,
        "repoCard": {"owner": owner, "name": name, "title": rc.get("title", name), "description": rc["description"], "language": rc.get("language"),
                     "license": rc.get("license")},
    }


def mix_vo(scenes: list[dict], voice: list[dict], seconds: float) -> np.ndarray:
    vo = np.zeros(math.ceil(seconds * RATE), np.float32)
    for s, v in zip(scenes, voice):
        pcm, _ = sf.read(v["wav"], dtype="float32")
        fx._mix(vo, pcm, s["from"] / FPS + s["lead_s"])
    return vo


# ---------------------------------------------------------------- hook variants
def hook_variant(spec: dict, cfg: dict, rec: dict, v: dict, scenes: list[dict], voice: list[dict], vcfg, work: Path, out: Path, name: str) -> dict:
    """A 3–5 s preview of one opening: the variant's shock beat (own narration, headline, shots) cut into the first spoken name of the
    context beat, so it ends on a word, not mid-sentence. Same voice speed as the episode."""
    vwork = work / f"hook-{v['id']}"
    story = {"scenes": [{"id": "shock", "kind": "shock", "narration": v["narration"], "lead_s": .05, "min_tail_s": .2, "hold": 1}],
             "voice_speed": voice[0]["speed"], "pacing": {"target_s": 0}}
    key = hashlib.sha256(json.dumps(story, sort_keys=True).encode()).hexdigest()[:16]
    cache = vwork / "voice.json"
    if cache.exists() and json.loads(cache.read_text()).get("key") == key:
        vv = json.loads(cache.read_text())["voice"]
    else:
        vv = bi.narrate(story, vcfg, work=vwork, pronounce=cfg.get("pronounce", {}))
        cache.write_text(json.dumps({"key": key, "voice": vv}))
    shock = bi.timeline(story, vv)[0]
    base = next(s for s in scenes if s["id"] == "shock")
    shock = {**shock, **{k: base[k] for k in base if k not in ("from", "frames", "words", "speech_s", "lead_s", "narration")}, "narration": v["narration"],
             "headline": v["headline"], "headline_at": v.get("headline_at", ["", ""]),
             **{k: v[k] for k in ("shots", "text") if v.get(k)}}
    ctx = dict(next(s for s in scenes if s["id"] == "context"))
    first = ctx["words"][0]
    ctx_frames = round((first["e"] + .35) * FPS)
    ctx = {**ctx, "from": shock["frames"], "frames": ctx_frames}
    pscenes = [shock, ctx]
    seconds = (shock["frames"] + ctx_frames) / FPS
    cvoice = next(x for x in voice if x["id"] == "context")
    pvoice = [vv[0], cvoice]
    words = [{"w": w["w"], "s": s["from"] / FPS + w["s"], "e": s["from"] / FPS + w["e"]} for s in pscenes for w in s["words"] if w["s"] < s["frames"] / FPS]
    subs = series.subtitle_groups(words, spec.get("emphasis", []), cfg["subtitles"]["min_words"], cfg["subtitles"]["max_words"])
    subs[-1]["e"] = min(subs[-1]["e"], seconds)
    props = reel_props(spec, cfg, rec, pscenes, subs, fx.mouth_envelope(mix_vo(pscenes, pvoice, seconds), FPS))
    (vwork / "props.json").write_text(json.dumps(props))
    info = bi.mix(pscenes, pvoice, cues(pscenes), seconds, work=vwork, music_on=True, out_name="mix.wav")
    silent = vwork / "silent.mp4"
    bi.remotion("SeriesReel", silent, vwork / "props.json", vcfg)
    dest = out / f"{name}-hook-{v['id']}.mp4"
    loud = be.master_tp(silent, vwork / "mix.wav", dest)
    return {"id": v["id"], "name": v.get("name"), "narration": v["narration"], "headline": v["headline"], "file": dest.name, "seconds": round(seconds, 2),
            "loudness": loud, "caveat": v.get("caveat"), "bed_gain_db": info.get("bed_gain_db"), "subtitles": subs}


# ---------------------------------------------------------------- Instagram overlay previews
def ig_overlay_filter(guides: bool) -> str:
    """Approximate Reels chrome at 1080x1920 (top bar, right action rail, bottom caption block), drawn over a frame; with guides the
    safe area is outlined too. A simulation for layout checks, not Instagram's exact UI."""
    t = lambda text, x, y, size, c="white": f"drawtext=fontfile={FONT}:text='{text}':x={x}:y={y}:fontsize={size}:fontcolor={c}"
    parts = ["drawbox=x=0:y=0:w=1080:h=210:color=black@0.35:t=fill", t("Reels", 48, 112, 52), "drawbox=x=966:y=112:w=60:h=48:color=white@0.9:t=4",
             "drawbox=x=0:y=1480:w=1080:h=440:color=black@0.45:t=fill"]
    for i, (y, label) in enumerate([(1120, "12.3K"), (1270, "214"), (1420, "1,024"), (1570, ""), (1690, "")]):
        parts.append(f"drawbox=x=930:y={y}:w=76:h=70:color=white@0.92:t=6")
        if label:
            parts.append(t(label, 936, y + 82, 30))
    parts += ["drawbox=x=40:y=1612:w=84:h=84:color=white@0.9:t=fill", t("devmimo", 142, 1622, 40), "drawbox=x=330:y=1614:w=150:h=58:color=white@0.9:t=3",
              t("Follow", 350, 1626, 34), t("Someone recreated seven Adobe-style apps…", 40, 1730, 38), t("more", 40, 1780, 36, "white@0.7"),
              t("Original audio · devmimo", 40, 1846, 32, "white@0.85"), "drawbox=x=930:y=1820:w=76:h=76:color=white@0.9:t=4"]
    if guides:
        sz = LAYOUT["safe"]
        parts.append(f"drawbox=x={sz['left']}:y={sz['top']}:w={sz['right'] - sz['left']}:h={sz['bottom'] - sz['top']}:color=0x33ff66:t=5")
    return ",".join(parts)


def ig_previews(video: Path, scenes: list[dict], qa: Path) -> list[dict]:
    """Key frames with the simulated Reels UI on top (with and without safe-area guides), plus one contact sheet of them."""
    by = {s["id"]: s for s in scenes}
    pick = []
    sh = by["shock"]
    pick.append(("hook-0.5s", .5))
    pick.append(("hook-headline", (sh["from"] + sh["frames"] - 4) / FPS))
    pick.append(("context-header", (by["context"]["from"] + by["context"]["frames"] * .6) / FPS))
    pick.append(("mystery-question", (by["mystery"]["from"] + by["mystery"]["frames"] - 6) / FPS))
    pick.append(("repository", (by["discovery"]["from"] + by["discovery"]["frames"] - 6) / FPS))
    pr = by["proof"]
    pick.append(("demo-disassembly", (pr["from"] + at_word(pr, pr["steps"][1]["at"], pr["frames"] // 2) + 20) / FPS))
    pick.append(("demo-findings", (pr["from"] + pr["frames"] - 4) / FPS))
    po = by["possibility"]
    pick.append(("rebuild-match", (po["from"] + po["frames"] - 4) / FPS))
    q = by["question"]
    pick.append(("cta", (q["from"] + q["frames"] - 3) / FPS))
    d = qa / "instagram"
    d.mkdir(parents=True, exist_ok=True)
    out = []
    for label, t in pick:
        for guides in (False, True):
            f = d / f"{label}{'-guides' if guides else ''}.png"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-vf", ig_overlay_filter(guides), str(f)],
                           check=True, timeout=120)
        out.append({"label": label, "t": round(t, 2), "file": str((d / f"{label}-guides.png").relative_to(qa.parent))})
    inputs = sum([["-i", str(d / f"{lab}-guides.png")] for lab, _ in pick], [])
    n = len(pick)
    filt = "".join(f"[{i}]scale=360:640[s{i}];" for i in range(n)) + "".join(f"[s{i}]" for i in range(n)) + f"xstack=inputs={n}:layout=" + "|".join(
        f"{(i % 5) * 360}_{(i // 5) * 640}" for i in range(n)) + ":fill=0x111114"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", filt, "-frames:v", "1", str(qa / "instagram-safe-preview.png")], check=True, timeout=120)
    return out


# ---------------------------------------------------------------- copy
def script_markdown(spec: dict, cfg: dict, n: int, scenes: list[dict], wpm: float, words: int, hooks: list[dict]) -> str:
    beats = {b["id"]: b for b in spec["beats"]}
    lines = [f"# {series.fmt(n)} · {spec['title']}", "", f"{cfg['name']} · repository: https://github.com/{series.normalize_repo(spec['repository'])}",
             f"Format: reel-v2 (shock → context → mystery → discovery → proof → possibility → question) · demo status: **{spec['demo']['status']}**", "",
             "| Beat | Start | Length | Narration | On screen |", "|---|---|---|---|---|"]
    for s in scenes:
        b = beats[s["id"]]
        shown = " / ".join(x["text"] for x in b.get("claims", [])) or " / ".join(b.get("text", [])) or "—"
        lines.append(f"| {s['id']} | {s['from'] / FPS:.2f}s | {s['frames'] / FPS:.2f}s | {b['narration']} | {shown} |")
    lines += ["", f"{words} words, {wpm:.0f} wpm while speaking.", "", "## Hook variants", ""]
    for h in hooks:
        lines.append(f"- **{h['id'].upper()} · {h['name']}** ({h['seconds']:.1f}s, `{h['file']}`): “{h['narration']}” — on screen: {' / '.join(h['headline'])}"
                     + (f" — caveat: {h['caveat']}" if h.get("caveat") else ""))
    lines += ["", f"Selected: **{spec.get('selected_hook', 'a').upper()}** (see the QA report for the comparison).", "", "## Verified features shown", ""]
    for f in spec["verified_features"]:
        lines.append(f"- **{f['label']}** ({f['status']}): {f['claim']} — evidence: {f['evidence']}")
    lines += ["", "## Demonstration notes", ""] + [f"- {x}" for x in spec["demo"].get("notes", [])]
    return "\n".join(lines) + "\n"


def caption_markdown(spec: dict, cfg: dict, n: int) -> str:
    cap = series.caption(spec, cfg, n)
    pin = spec.get("caption", {}).get("pinned_comment")
    return f"# Instagram caption · {series.fmt(n)}\n\n```\n{cap.rstrip()}\n```\n" + (f"\n## Pinned comment\n\n```\n{pin}\n```\n" if pin else "")


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", type=Path)
    ap.add_argument("--episode", type=int)
    ap.add_argument("--series-root", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--reuse-voice", action="store_true")
    ap.add_argument("--validate-only", action="store_true")
    ap.add_argument("--skip-render", action="store_true")
    ap.add_argument("--skip-hooks", action="store_true", help="keep the hook previews already in the output folder")
    a = ap.parse_args()
    started = time.time()
    spec = json.loads(a.spec.read_text())
    if not series.is_reel(spec):
        raise SystemExit("not a reel-v2 spec; use build_episode.py")
    slug = spec["series"]
    cfg = merged_cfg(spec, series.config(slug, a.series_root))
    errs = series.validate(spec, cfg)
    if errs:
        raise SystemExit("spec rejected:\n  - " + "\n  - ".join(errs))
    be.fetch_media(spec)
    missing = [m for m in media_refs(spec) if not (ROOT / "public" / m).exists()]
    if missing:
        raise SystemExit("spec rejected: media not found under public/: " + ", ".join(missing))
    if a.validate_only:
        print("spec OK (nothing allocated)")
        return
    rec, created = series.allocate(slug, spec["repository"], spec["title"], a.episode, a.series_root)
    n = rec["episode"]
    print(f"{series.fmt(n)} {'reserved' if created else 'kept (already allocated to this repository)'}: {rec['repository']}")
    name = f"episode-{n:03d}"
    out = a.out or ROOT / "outputs" / slug / name
    work = ROOT / "data" / "series" / slug / name
    (out / "qa").mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)

    story = storyboard(spec, cfg)
    vcfg = settings.load()
    key = hashlib.sha256(json.dumps([story["scenes"], story["voice_speed"], cfg["pacing"]["wpm_target"]], sort_keys=True).encode()).hexdigest()[:16]
    cache = work / "voice.json"
    if a.reuse_voice and cache.exists() and json.loads(cache.read_text()).get("key") == key:
        voice = json.loads(cache.read_text())["voice"]
    else:
        voice = be.fit_voice(story, vcfg, work, cfg)
        cache.write_text(json.dumps({"key": key, "voice": voice}))
    timed = bi.timeline(story, voice)
    scenes = beat_scenes(spec, timed)
    frames = sum(s["frames"] for s in scenes)
    seconds = frames / FPS
    words = [{"w": w["w"], "s": s["from"] / FPS + w["s"], "e": s["from"] / FPS + w["e"]} for s in scenes for w in s["words"]]
    subs = series.subtitle_groups(words, spec.get("emphasis", []), cfg["subtitles"]["min_words"], cfg["subtitles"]["max_words"])
    subs[-1]["e"] = min(subs[-1]["e"], seconds)
    props = reel_props(spec, cfg, rec, scenes, subs, fx.mouth_envelope(mix_vo(scenes, voice, seconds), FPS))
    cue_list = cues(scenes)
    info = bi.mix(scenes, voice, cue_list, seconds, work=work, music_on=True, out_name="mix.wav")
    bi.mix(scenes, voice, cue_list, seconds, work=work, music_on=False, out_name="mix-nomusic.wav")
    (work / "props.json").write_text(json.dumps(props))
    print(json.dumps({"seconds": seconds, "beats": [(s["id"], s["from"], s["frames"], round(s["speech_s"], 2)) for s in scenes]}))
    if a.skip_render:
        return

    print("render…")
    silent = work / "silent.mp4"
    bi.remotion("SeriesReel", silent, work / "props.json", vcfg)
    final, nomusic = out / f"{name}-final.mp4", out / f"{name}-no-music.mp4"
    loud = {"final": be.master_tp(silent, work / "mix.wav", final), "no_music": be.master_tp(silent, work / "mix-nomusic.wav", nomusic)}
    hooks_file = work / "hooks.json"
    if a.skip_hooks and hooks_file.exists():
        hooks = json.loads(hooks_file.read_text())
    else:
        hooks = [hook_variant(spec, cfg, rec, v, scenes, voice, vcfg, work, out, name) for v in spec.get("hook_variants", [])]
        hooks_file.write_text(json.dumps(hooks))
    cover_props = work / "cover.json"
    cover_props.write_text(json.dumps({"series": props["series"], "episode": props["episode"]}))
    bi.remotion("SeriesCover", out / f"{name}-cover.png", cover_props, vcfg, still=0)
    be.cover_crops(out / f"{name}-cover.png", out / f"{name}-cover-4x5.png", out / f"{name}-cover-square.png")
    (work / "cover-mask.json").write_text(json.dumps({"series": props["series"], "episode": props["episode"], "mask": True}))
    bi.remotion("SeriesCover", out / "qa" / "cover-mask.png", work / "cover-mask.json", vcfg, still=0)
    bi.remotion("SeriesCoverGuides", out / "qa" / "cover-guides.png", cover_props, vcfg, still=0)
    be.grid_preview(out / f"{name}-cover-square.png", out / "qa" / "cover-grid-thumbnail.png")
    bi.contact_sheet(final, out / "qa" / "contact-sheet.png", seconds)
    ig = ig_previews(final, scenes, out / "qa")

    import qa_reel
    total_words = sum(len(s["words"]) for s in scenes)
    wpm = 60 * total_words / sum(s["speech_s"] for s in scenes)
    report = qa_reel.run(out, name, props, spec, cfg, loud, voice, hooks)
    (out / f"{name}-caption.md").write_text(caption_markdown(spec, cfg, n))
    (out / f"{name}-script.md").write_text(script_markdown(spec, cfg, n, scenes, wpm, total_words, hooks))
    research = ROOT / "series" / slug / "research" / f"{name}-research.md"
    if research.exists():
        shutil.copy(research, out / f"{name}-research.md")
    files = {"final": f"{name}-final.mp4", "no_music": f"{name}-no-music.mp4", "cover": f"{name}-cover.png", "cover_4x5": f"{name}-cover-4x5.png",
             "cover_square": f"{name}-cover-square.png", "script": f"{name}-script.md", "caption": f"{name}-caption.md", "research": f"{name}-research.md",
             "metadata": f"{name}-metadata.json", "qa_report": f"{name}-qa-report.md", **{f"hook_{h['id']}": h["file"] for h in hooks}}
    outputs = {k: str((out / f).relative_to(ROOT) if (out / f).is_relative_to(ROOT) else out / f) for k, f in files.items()}
    meta = {
        "series": cfg["name"], "series_slug": slug, "episode": n, "episode_label": series.fmt(n), "title": spec["title"], "format": "reel-v2",
        "cover_headline": " ".join(spec["cover_headline"]), "github_url": f"https://github.com/{props['episode']['repo']}",
        "repository": props["episode"]["repo"], "repository_description": spec["repo_card"]["description"], "category": spec.get("category"),
        "verified_features": spec["verified_features"],
        "demonstration": {"status": spec["demo"]["status"], "meaning": series.DEMO_STATUSES[spec["demo"]["status"]], "on_screen_tag": spec["demo"].get("tag"),
                          "notes": spec["demo"].get("notes", [])},
        "verification": spec.get("verification", {}), "source_references": spec.get("verification", {}).get("sources", []),
        "narration_script": series.default_narration(spec, cfg), "narration_word_count": total_words, "speaking_rate_wpm": round(wpm, 1),
        "word_timing_source": voice[0].get("timing_source"),
        "voice": {"engine": voice[0]["engine"], "voice": voice[0]["voice"], "speed": voice[0].get("speed"), "speed_search": voice[0].get("speed_search")},
        "duration_s": round(seconds, 3), "beats": [{"id": s["id"], "start_s": round(s["from"] / FPS, 2), "seconds": round(s["frames"] / FPS, 2)} for s in scenes],
        "hook_variants": [{k: v for k, v in h.items() if k != "subtitles"} for h in hooks], "selected_hook": spec.get("selected_hook", "a"),
        "instagram_caption": series.caption(spec, cfg, n), "pinned_comment": spec.get("caption", {}).get("pinned_comment"),
        "hashtags": [t for t in series.caption(spec, cfg, n).split() if t.startswith("#")], "instagram_previews": ig,
        "safe_zone": cfg["safe_zone"]["reel_v2"], "publication_status": "draft", "outputs": outputs, "loudness": loud,
        "music_bed_gain_db": info.get("bed_gain_db"), "qa_summary": report["summary"], "build_seconds": round(time.time() - started, 1),
        "never_included": "no GitHub stars, forks, downloads, contributor counts or other repository statistics; no engagement predictions",
    }
    (out / f"{name}-metadata.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    (out / f"{name}-qa-report.md").write_text(qa_reel.markdown(report, meta))
    series.update(slug, n, a.series_root, status="rendered", title=spec["title"], rendered_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                  outputs=outputs, demo_status=spec["demo"]["status"], format="reel-v2")
    print(json.dumps(report["summary"], indent=1))


if __name__ == "__main__":
    main()
