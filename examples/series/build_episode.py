"""Build one episode of a recurring series from its spec: number → narration → timing → subtitles → sound → render → covers → QA →
metadata. Built on the V2.2 pieces the DevMimo intro already uses (Kokoro narration, reference EQ, SFX palette, warm-pad bed,
iterative master, Remotion CLI); nothing in the pipeline is rebuilt.

    .venv/bin/python examples/series/build_episode.py series/mimo-found-this-on-github/specs/<repo>.json
    .venv/bin/python examples/series/build_episode.py SPEC --episode 7        # manual number (refused if taken by another repo)
    .venv/bin/python examples/series/build_episode.py SPEC --reuse-voice      # keep cached narration
    .venv/bin/python examples/series/build_episode.py SPEC --validate-only    # check claims and copy, allocate nothing

A spec only needs: repository, title, cover headline, verified features (with evidence), the demo (status + panels) and optional
narration / mascot expression. Everything else (number, layout, covers, subtitles, captions, QA) comes from the series system.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
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

import build_intro as bi  # noqa: E402  (narrate, timeline, sfx_track, mix, remotion, master, contact_sheet)
from video_mcp import audio as fx, series, settings  # noqa: E402
from video_mcp.audio import RATE  # noqa: E402

FPS = bi.FPS
LAYOUT = json.loads((ROOT / "src" / "series" / "layout.json").read_text())
# Scene order and default pacing weights; narration keys map to scene kinds.
SCENES = [("hook", "hook", .05, .35, .5), ("discovery", "discovery", .15, .35, .5), ("demo", "demo", .2, .5, 1.6),
          ("tech", "flow", .2, .45, 1.1), ("payoff", "payoff", .15, .55, .5)]
DEMO_TAGS = {"captured": None, "run-in-sandbox": "RE-DRAWN FROM A SANDBOX RUN", "source-reenactment": "RE-ENACTED FROM SOURCE",
             "project-showcase": "OFFICIAL DEMO", "fixture": "PIPELINE TEST · NOT AN EPISODE"}


def media_refs(spec: dict) -> list[str]:
    """Every image / video the episode shows (panel sources and cover assets), as paths under public/."""
    refs = []
    for v in spec.get("project_visual_assets", {}).values():
        refs += v if isinstance(v, list) else [v]

    def walk(x):
        if isinstance(x, dict):
            if x.get("kind") in ("image", "video") and x.get("src"):
                refs.append(x["src"])
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(spec.get("demo", {}))
    return sorted(set(refs))


def fetch_media(spec: dict):
    """Download published media the spec cites (spec.media_sources: {public path: URL}) when it is not on disk yet. Renders are
    git-ignored, so this is how a fresh checkout gets a project's official demo videos back."""
    for rel, url in spec.get("media_sources", {}).items():
        dest = ROOT / "public" / rel
        if dest.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"fetch {url}")
        subprocess.run(["curl", "-sSLf", "--max-time", "300", "-o", str(dest), url], check=True)


def storyboard(spec: dict, cfg: dict) -> dict:
    narration = series.default_narration(spec, cfg)
    pacing = {**cfg["pacing"], **spec.get("pacing", {})}
    scenes = []
    for key, kind, lead, tail, hold in SCENES:
        o = spec.get("scene_timing", {}).get(key, {})
        scenes.append({"id": key, "kind": kind, "narration": narration[key], "lead_s": o.get("lead_s", lead), "min_tail_s": o.get("min_tail_s", tail),
                       "hold": o.get("hold", hold)})
    return {"scenes": scenes, "voice_speed": pacing["voice_speed"],
            "pacing": {"target_s": pacing["target_s"] - pacing["outro_s"], "wpm_target": pacing["wpm_target"]}}


# ---------------------------------------------------------------- cue frames (same formulas as src/series/Episode.tsx)
def wf(scene: dict, i: int) -> int:
    w = scene["words"][i if i >= 0 else len(scene["words"]) + i]
    return round(w["s"] * FPS)


def label_frame(scene: dict, labels: list[dict], i: int) -> int:
    """Chips land in order (a label never appears before the one to its left)."""
    own = lambda l, j: wf(scene, l["at"]) if "at" in l else round(scene["frames"] * (.15 + .6 * j / max(1, len(labels))))
    return max(own(l, j) for j, l in enumerate(labels[:i + 1]))


def press_times(path: list[dict], start: float, end: float) -> list[float]:
    """Moments a keyed path's pinch crosses 0.7 upward (the cursor panel draws a press ripple there)."""
    out, prev = [], None
    t = start
    while t <= end:
        k = sample(path, t)
        if prev is not None and prev < .7 <= k:
            out.append(t)
        prev, t = k, t + 1 / FPS
    return out


def sample(path: list[dict], t: float) -> float:
    if not path:
        return 0.0
    if t <= path[0]["t"]:
        return path[0].get("pinch", 0)
    for a, b in zip(path, path[1:]):
        if t <= b["t"]:
            k = (t - a["t"]) / max(1e-6, b["t"] - a["t"])
            k = 4 * k ** 3 if k < .5 else 1 - (-2 * k + 2) ** 3 / 2          # Easing.inOut(cubic), as in theme.ts samplePath
            return a.get("pinch", 0) + (b.get("pinch", 0) - a.get("pinch", 0)) * k
    return path[-1].get("pinch", 0)


def cues(scenes: list[dict], props: dict) -> list[dict]:
    by = {s["kind"]: s for s in scenes}
    out = []
    add = lambda kind, frame, sound, gain, **kw: out.append({"scene": by[kind]["id"], "frame": max(0, int(frame)), "sound": sound, "gain": gain, **kw})
    hook = by["hook"]
    add("hook", 0, "tick", .55)                                          # subtle electronic click + short bass accent
    add("hook", 0, "boom", .35)
    lines = props["episode"]["headline"]
    for i in range(1, len(lines)):
        add("hook", wf(hook, round(i * len(hook["words"]) / len(lines))), "pop", .45)
    for panel in props["hook"]["panels"]:
        if panel["kind"] == "cursor":
            for t in press_times(panel["path"], 0, hook["frames"] / FPS):
                add("hook", t * FPS, "tick", .5)
    add("discovery", 0, "whoosh", .35)
    add("discovery", 10, "whoosh", .3)
    add("discovery", 22, "pop", .4)
    demo = by["demo"]
    labels = props["demo"]["labels"]
    for i, lab in enumerate(labels):
        add("demo", label_frame(demo, labels, i), "tick", .5)
    add("demo", 10, "plug", .3)
    if props["demo"].get("output") and len(labels) > 1:                 # before -> after: the output lands with the second stage
        add("demo", label_frame(demo, labels, 1), "whoosh", .4)
        add("demo", label_frame(demo, labels, len(labels) - 1) + 2, "chime", .3)
    right = props["demo"]["right"] or {}
    if right.get("kind") == "cursor":
        for t in press_times(right["path"], 0, demo["frames"] / FPS):
            add("demo", t * FPS, "tick", .45)
    flow = by["flow"]
    n = len(props["flow"])
    for i in range(n):
        add("flow", round(8 + i * min(26, (flow["frames"] - 50) / max(1, n))), "tick", .45)
    pay = by["payoff"]
    add("payoff", 4, "chime", .3)
    follow = next((i for i, w in enumerate(pay["words"]) if w["w"].lower().startswith("follow")), None)
    add("payoff", wf(pay, follow) if follow is not None else round(pay["frames"] * .55), "stamp", .45)
    add("outro", 0, "pop", .35)
    add("outro", 12, "chime", .3)
    return out


# ---------------------------------------------------------------- props
def wpm_of(voice: list[dict]) -> float:
    return 60 * sum(len(v["words"]) for v in voice) / sum(v["seconds"] for v in voice)


def fit_voice(story: dict, vcfg, work: Path, cfg: dict) -> list[dict]:
    """Narrate, measure the speaking rate, and re-narrate at an adjusted Kokoro speed until it lands in the series target (145–165
    wpm). Word length changes the rate a lot (short words read faster) and the response to the speed setting is not linear, so the
    search interpolates between the two closest attempts. Audio is never time-stretched."""
    lo, hi = cfg["pacing"]["wpm_target"]
    mid = (lo + hi) / 2
    speed, tries = story["voice_speed"], []
    for attempt in range(5):
        story["voice_speed"] = round(speed, 3)
        print(f"narration (Kokoro @ {speed:.3f}):")
        voice = bi.narrate(story, vcfg, work=work, pronounce=cfg.get("pronounce", {}))
        wpm = wpm_of(voice)
        print(f"  {wpm:.0f} wpm while speaking")
        tries.append((speed, wpm))
        if lo + 2 <= wpm <= hi - 2:
            break
        below = [t for t in tries if t[1] < mid]
        above = [t for t in tries if t[1] > mid]
        if below and above:
            (s1, w1), (s2, w2) = max(below, key=lambda t: t[1]), min(above, key=lambda t: t[1])
            speed = s1 + (s2 - s1) * (mid - w1) / (w2 - w1)
        else:
            speed = min(1.15, max(.75, speed * mid / wpm))
    for v in voice:
        v["speed"] = story["voice_speed"]
        v["speed_search"] = [{"speed": round(a, 3), "wpm": round(b, 1)} for a, b in tries]
    return voice


def master_tp(silent: Path, wav: Path, out: Path, lufs: float = -14.0) -> dict:
    """Linear gain to the target + a 4x-oversampled (true-peak) limiter, AAC 192k. Oversampling keeps AAC overshoot under −1 dBTP,
    so the loop only has to correct loudness (the intro's sample-peak master fought the encoder on peaky mixes)."""
    from video_mcp import audio_profile
    gain, limit, best = lufs - audio_profile.loudness(wav)["integrated_lufs"], .79, None
    for _ in range(6):
        chain = f"volume={gain:.2f}dB,aresample=192000,alimiter=limit={limit:.3f}:attack=1:release=80:level=false,aresample=48000"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(silent), "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                        "-af", chain, "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)], check=True, timeout=600)
        m = audio_profile.loudness(out)
        if abs(m["integrated_lufs"] - lufs) <= .3 and m["true_peak_dbtp"] <= -1.0:
            return m
        if m["true_peak_dbtp"] > -1.0:
            limit *= 10 ** ((-1.3 - m["true_peak_dbtp"]) / 20)
        gain += lufs - m["integrated_lufs"]
    return m


def episode_props(spec: dict, cfg: dict, rec: dict, scenes: list[dict], subs: list[dict], mouth: list[float], outro_frames: int) -> dict:
    owner, name = series.normalize_repo(spec["repository"]).split("/")
    demo = spec["demo"]
    status = demo["status"]
    return {
        "fps": FPS, "durationInFrames": sum(s["frames"] for s in scenes) + outro_frames, "outroFrames": outro_frames,
        "series": {k: cfg[k] for k in ("header", "tagline", "footer", "handle", "collection")},
        "episode": {"n": rec["episode"], "label": series.fmt(rec["episode"]), "title": spec["title"], "repo": f"{owner}/{name}",
                    "category": spec.get("category", "Open source"), "headline": spec["cover_headline"],
                    "expression": spec.get("mascot_expression", "surprised"), "visual": spec.get("project_visual", "terminal"),
                    "demoStatus": status, "demoTag": demo.get("tag", DEMO_TAGS[status]), "visualAssets": spec.get("project_visual_assets", {}),
                    **({"hookHeadline": spec["hook_headline"]} if spec.get("hook_headline") else {})},
        "scenes": [{**s, "narration": next(x["narration"] for x in storyboard(spec, cfg)["scenes"] if x["id"] == s["id"])} for s in scenes],
        "subtitles": subs, "mouth": mouth,
        "hook": {"panels": demo["hook"]["panels"], "labels": demo["hook"].get("labels", [])},
        "demo": {"left": demo["demo"].get("left"), "right": demo["demo"].get("right"), "labels": demo["demo"].get("labels", []),
                 **{k: demo["demo"][k] for k in ("input", "output") if k in demo["demo"]}},
        "flow": spec.get("flow", []),
        "repoCard": {"owner": owner, "name": name, "description": spec["repo_card"]["description"],
                     "language": spec["repo_card"].get("language"), "license": spec["repo_card"].get("license")},
        "payoff": {"panel": demo.get("payoff", {}).get("panel", demo["hook"]["panels"][0]),
                   "question": demo.get("payoff", {}).get("question", "WOULD YOU TRY THIS?"),
                   "replayFrom": demo.get("payoff", {}).get("replay_from", 0)},
    }


def cover_crops(master: Path, out4x5: Path, square: Path):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(master), "-vf", "crop=1080:1350:0:285", str(out4x5)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(master), "-vf", "crop=1080:1080:0:420", str(square)], check=True)


def grid_preview(square: Path, out: Path):
    """The square cover at real profile-grid size (3 columns on a 1080-px-wide phone = 357 px), beside two neutral tiles."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(square), "-filter_complex",
                    "[0]scale=357:357[a];color=c=0x2a2b30:s=357x357[b];color=c=0x2a2b30:s=357x357[c];[b][a][c]hstack=3,pad=1083:369:0:6:color=0xffffff",
                    "-frames:v", "1", str(out)], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", type=Path)
    ap.add_argument("--episode", type=int, help="manual episode number (refused if another repository holds it)")
    ap.add_argument("--series-root", type=Path, help="registry root (tests use a temporary one); default series/")
    ap.add_argument("--out", type=Path, help="output folder; default outputs/<series>/episode-NNN")
    ap.add_argument("--reuse-voice", action="store_true")
    ap.add_argument("--validate-only", action="store_true")
    ap.add_argument("--skip-render", action="store_true")
    a = ap.parse_args()
    started = time.time()
    spec = json.loads(a.spec.read_text())
    slug = spec["series"]
    cfg = series.config(slug, a.series_root)
    errs = series.validate(spec, cfg)
    if errs:
        raise SystemExit("spec rejected:\n  - " + "\n  - ".join(errs))
    fetch_media(spec)
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
    key = hashlib.sha256(json.dumps([story["scenes"], story["voice_speed"]], sort_keys=True).encode()).hexdigest()[:16]
    cache = work / "voice.json"
    if a.reuse_voice and cache.exists() and json.loads(cache.read_text()).get("key") == key:
        voice = json.loads(cache.read_text())["voice"]
    else:
        voice = fit_voice(story, vcfg, work, cfg)
        cache.write_text(json.dumps({"key": key, "voice": voice}))
    scenes = bi.timeline(story, voice)
    outro_frames = round(cfg["pacing"]["outro_s"] * FPS)
    frames = sum(s["frames"] for s in scenes) + outro_frames
    seconds = frames / FPS

    words = [{"w": w["w"], "s": s["from"] / FPS + w["s"], "e": s["from"] / FPS + w["e"]} for s in scenes for w in s["words"]]
    subs = series.subtitle_groups(words, spec.get("emphasis", []), cfg["subtitles"]["min_words"], cfg["subtitles"]["max_words"])
    vo = np.zeros(math.ceil(seconds * RATE), np.float32)
    for s, v in zip(scenes, voice):
        pcm, _ = sf.read(v["wav"], dtype="float32")
        fx._mix(vo, pcm, s["from"] / FPS + s["lead_s"])
    props = episode_props(spec, cfg, rec, scenes, subs, fx.mouth_envelope(vo, FPS), outro_frames)
    cue_list = cues(scenes + [{"id": "outro", "kind": "outro", "from": frames - outro_frames, "frames": outro_frames, "words": []}], props)
    timed = scenes + [{"id": "outro", "kind": "outro", "from": frames - outro_frames, "frames": outro_frames, "words": [], "lead_s": 0}]
    info = bi.mix(timed, voice, cue_list, seconds, work=work, music_on=True, out_name="mix.wav")
    bi.mix(timed, voice, cue_list, seconds, work=work, music_on=False, out_name="mix-nomusic.wav")
    (work / "props.json").write_text(json.dumps(props))
    if a.skip_render:
        print(json.dumps({"seconds": seconds, "scenes": [(s["id"], s["from"], s["frames"]) for s in scenes]}, indent=1))
        return

    print("render…")
    silent = work / "silent.mp4"
    bi.remotion("SeriesEpisode", silent, work / "props.json", vcfg)
    final, nomusic = out / f"{name}-final.mp4", out / f"{name}-no-music.mp4"
    loud = {"final": master_tp(silent, work / "mix.wav", final), "no_music": master_tp(silent, work / "mix-nomusic.wav", nomusic)}
    cover_props = work / "cover.json"
    cover_props.write_text(json.dumps({"series": props["series"], "episode": props["episode"]}))
    bi.remotion("SeriesCover", out / f"{name}-cover.png", cover_props, vcfg, still=0)
    cover_crops(out / f"{name}-cover.png", out / f"{name}-cover-4x5.png", out / f"{name}-cover-square.png")
    (work / "cover-mask.json").write_text(json.dumps({"series": props["series"], "episode": props["episode"], "mask": True}))
    bi.remotion("SeriesCover", out / "qa" / "cover-mask.png", work / "cover-mask.json", vcfg, still=0)
    bi.remotion("SeriesCoverGuides", out / "qa" / "cover-guides.png", cover_props, vcfg, still=0)
    grid_preview(out / f"{name}-cover-square.png", out / "qa" / "cover-grid-thumbnail.png")
    bi.contact_sheet(final, out / "qa" / "contact-sheet.png", seconds)

    sys.path.insert(0, str(HERE))
    import qa_episode
    report = qa_episode.run(out, name, props, spec, cfg, loud, voice)
    total_words = sum(len(s["words"]) for s in scenes)
    speech = sum(s["speech_s"] for s in scenes)
    wpm = 60 * total_words / speech
    narration = series.default_narration(spec, cfg)
    caption = series.caption(spec, cfg, n)
    (out / f"{name}-caption.md").write_text(caption)
    (out / f"{name}-script.md").write_text(series.script_markdown(spec, cfg, n, props["scenes"], wpm, total_words))
    outputs = {k: str((out / f).relative_to(ROOT) if (out / f).is_relative_to(ROOT) else out / f) for k, f in {
        "final": f"{name}-final.mp4", "no_music": f"{name}-no-music.mp4", "cover": f"{name}-cover.png", "cover_4x5": f"{name}-cover-4x5.png",
        "cover_square": f"{name}-cover-square.png", "script": f"{name}-script.md", "caption": f"{name}-caption.md",
        "metadata": f"{name}-metadata.json", "qa_report": f"{name}-qa-report.md"}.items()}
    meta = {
        "series": cfg["name"], "series_slug": slug, "episode": n, "episode_label": series.fmt(n), "title": spec["title"],
        "cover_headline": " ".join(spec["cover_headline"]), "github_url": f"https://github.com/{props['episode']['repo']}",
        "repository": props["episode"]["repo"], "repository_description": spec["repo_card"]["description"],
        "category": spec.get("category"), "verified_features": spec["verified_features"],
        "demonstration": {"status": spec["demo"]["status"], "meaning": series.DEMO_STATUSES[spec["demo"]["status"]],
                          "on_screen_tag": props["episode"]["demoTag"], "notes": spec["demo"].get("notes", [])},
        "verification": spec.get("verification", {}), "source_references": spec.get("verification", {}).get("sources", []),
        "narration_script": narration, "narration_word_count": total_words, "speaking_rate_wpm": round(wpm, 1),
        "word_timing_source": voice[0].get("timing_source"),
        "voice": {"engine": voice[0]["engine"], "voice": voice[0]["voice"], "speed": voice[0].get("speed"), "speed_search": voice[0].get("speed_search")},
        "duration_s": round(seconds, 3), "scenes": [{"id": s["id"], "start_s": round(s["from"] / FPS, 2), "seconds": round(s["frames"] / FPS, 2)} for s in scenes],
        "instagram_caption": caption, "hashtags": [t for t in caption.split() if t.startswith("#")],
        "publication_status": "draft", "outputs": outputs, "loudness": loud, "music_bed_gain_db": info.get("bed_gain_db"),
        "qa_summary": report["summary"], "build_seconds": round(time.time() - started, 1),
        "never_included": "no GitHub stars, forks, downloads, contributor counts or other repository statistics",
    }
    (out / f"{name}-metadata.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    (out / f"{name}-qa-report.md").write_text(qa_episode.markdown(report, meta))
    series.update(slug, n, a.series_root, status="rendered", title=spec["title"], rendered_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                  outputs=outputs, demo_status=spec["demo"]["status"])
    print(json.dumps(report["summary"], indent=1))


if __name__ == "__main__":
    main()
