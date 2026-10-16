#!/usr/bin/env python3
"""Build a creator reel around real gameplay recordings (reels/<id>/reel.json).

    .venv/bin/python examples/game_reel/build_game_reel.py reels/claude-game/reel.json [--clips DIR] [--reuse-voice] [--skip-render]

Footage: public/game-reel/<clip>.mp4 (1080x1920, 30 fps) plus the game's own audio as <clip>.wav in --clips (default data/game-reel/clips),
recorded with examples/game_reel/capture_gameplay.gd (Godot movie writer, deterministic). Narration: Kokoro at a measured 150–175 wpm,
the same voice chain as the DevMimo series. Every cut is resolved here to frames on the narration's word clock, so GameReel.tsx draws
only numbers. Outputs: outputs/reels/<id>/ (final, no-music, cover x3, script, caption, prompt, metadata, QA report, qa/ previews).
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
sys.path.insert(0, str(ROOT / "examples" / "series"))
sys.path.insert(0, str(HERE))

import build_intro as bi  # noqa: E402
import build_episode as be  # noqa: E402  (fit_voice, master_tp, cover_crops, grid_preview)
import build_reel as br  # noqa: E402  (at_word, ig_overlay_filter)
from video_mcp import audio as fx, audio_profile, series, settings  # noqa: E402
from video_mcp.audio import RATE  # noqa: E402

FPS = 30
LAYOUT = json.loads((ROOT / "src" / "gamereel" / "layout.json").read_text())
SUB = {"min_words": 3, "max_words": 5}


def clip_seconds(clip: str) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(ROOT / "public" / "game-reel" / f"{clip}.mp4")],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def story_of(spec: dict) -> dict:
    keys = ("id", "kind", "narration", "lead_s", "min_tail_s", "hold")
    return {"scenes": [{k: b[k] for k in keys if k in b} for b in spec["beats"]], "voice_speed": spec.get("voice_speed", 1.0),
            "pacing": {"target_s": spec["pacing"]["target_s"]}}


def resolve(spec: dict, timed: list[dict]) -> list[dict]:
    """Beat timing from the narration + every cut, label and overlay as absolute frames. Raises if a cut runs past its recording."""
    beats, errors = [], []
    lengths: dict[str, float] = {}

    def need(clip: str, src: float, frames: int, where: str):
        n = lengths.setdefault(clip, clip_seconds(clip))
        if src < 0 or src + frames / FPS > n - 1 / FPS:
            errors.append(f"{where}: {clip} needs {src:.2f}–{src + frames / FPS:.2f}s, recording is {n:.2f}s")

    for b, t in zip(spec["beats"], timed):
        sc = {"id": t["id"], "kind": t["kind"], "from": t["from"], "frames": t["frames"], "words": t["words"], "lead_s": t["lead_s"],
              "speech_s": t["speech_s"], "narration": b["narration"]}
        at = lambda tok, fb=0: t["from"] + br.at_word(sc, tok, fb)
        segs = b.get("segs", [])
        cuts = [0 if i == 0 else br.at_word(sc, s.get("at"), round(t["frames"] * i / len(segs))) for i, s in enumerate(segs)]
        out = []
        prompt = None
        if b.get("prompt"):
            out_f = round(t["frames"] * b["prompt"]["out_frac"])
            prompt = {"label": b["prompt"]["label"], "lines": b["prompt"]["lines"], "out": t["from"] + out_f}
        for i, s in enumerate(segs):
            start, end = cuts[i], cuts[i + 1] if i + 1 < len(segs) else t["frames"]
            frames = end - start
            if "src_end" in s:
                src = s["src_end"] - frames / FPS
            elif "reveal_src" in s and prompt:
                src = s["reveal_src"] - (prompt["out"] - t["from"] + 5) / FPS
            else:
                src = s["src"]
            need(s["clip"], src, frames, f"{b['id']} cut {i}")
            out.append({"clip": s["clip"], "src": round(src, 3), "from": t["from"] + start, "frames": frames, "crop_y": s.get("crop_y", 0)})
        sc["segs"] = out
        if prompt:
            sc["prompt"] = prompt
        if b.get("headline"):
            sc["headline"] = {**b["headline"], "at": at(b["headline"].get("at"))}
        if b.get("label"):
            sc["label"] = [{"text": x["text"], "at": at(x["at"])} for x in b["label"]]
        if b.get("pill"):
            sc["pill"] = {"text": b["pill"]["text"], "at": at(b["pill"]["at"], round(t["frames"] * .4))}
        if b.get("split"):
            sp = b["split"]
            for side in ("left", "right"):
                need(sp[side]["clip"], sp[side]["src"], t["frames"], f"{b['id']} {side}")
            sc["split"] = {"left": {**sp["left"], "from": t["from"], "frames": t["frames"]}, "right": {**sp["right"], "from": t["from"], "frames": t["frames"]},
                           "note": sp["note"]}
        if b.get("cta"):
            sc["cta"] = {**b["cta"], "at": at(b["cta"]["at"])}
        beats.append(sc)
    if errors:
        raise SystemExit("cuts run past their recordings:\n  - " + "\n  - ".join(errors))
    return beats


def game_audio(beats: list[dict], clips: Path, seconds: float) -> np.ndarray:
    """The game's own sound under each cut (taps, belts, deliveries, celebration), from the same recording as the picture."""
    track = np.zeros(math.ceil(seconds * RATE), np.float32)
    cache: dict[str, np.ndarray] = {}
    for b in beats:
        segs = b["segs"] or ([b["split"]["right"]] if b.get("split") else [])
        for s in segs:
            if s["clip"] not in cache:
                pcm, rate = sf.read(clips / f"{s['clip']}.wav", dtype="float32")
                assert rate == RATE, f"{s['clip']}.wav must be {RATE} Hz mono"
                cache[s["clip"]] = pcm if pcm.ndim == 1 else pcm.mean(axis=1)
            pcm = cache[s["clip"]]
            a, n = round(s["src"] * RATE), round(s["frames"] / FPS * RATE)
            piece = pcm[a:a + n].copy()
            fade = min(len(piece) // 2, round(.012 * RATE))      # no clicks at cuts
            if fade:
                piece[:fade] *= np.linspace(0, 1, fade)
                piece[-fade:] *= np.linspace(1, 0, fade)
            o = round(s["from"] / FPS * RATE)
            track[o:o + len(piece)] += piece[:len(track) - o]
    return track


def duck(track: np.ndarray, speech: list[tuple[float, float]], db: float = -7.0) -> np.ndarray:
    g = np.ones_like(track)
    for s, e in speech:
        g[max(0, round((s - .08) * RATE)):round((e + .12) * RATE)] = 10 ** (db / 20)
    k = round(.06 * RATE)
    g = np.convolve(g, np.ones(k) / k, mode="same")                 # smooth gain changes
    return track * g


def mix(beats: list[dict], voice: list[dict], clips: Path, seconds: float, work: Path) -> dict:
    n = math.ceil(seconds * RATE)
    vo = np.zeros(n, np.float32)
    speech, voices = [], []
    for b, v in zip(beats, voice):
        pcm, _ = sf.read(v["wav"], dtype="float32")
        voices.append(pcm)
        fx._mix(vo, pcm, b["from"] / FPS + b["lead_s"])
        speech += [(b["from"] / FPS + w["s"], b["from"] / FPS + w["e"]) for w in b["words"]]
    game = duck(game_audio(beats, clips, seconds)[:n], speech)
    # the game sits under the voice: its peaks 12 dB below the narration's peaks
    gpk, vpk = float(np.abs(game).max() or 1), float(np.abs(vo).max() or 1)
    game *= vpk / gpk * 10 ** (-12 / 20)
    prof = audio_profile.profile()
    bed_cfg = prof["targets"]["music"]
    fx.music_bed(work / "music-raw.wav", seconds, 96, 3, speech, style=bed_cfg.get("style", "warm_pad"), duck_db=bed_cfg.get("duck_db", -6))
    music, _ = sf.read(work / "music-raw.wav", dtype="float32")
    gain = audio_profile.bed_gain_db(voices, music, RATE, prof["measured"]["bed_minus_speech_db"])
    music = music[:n] * 10 ** (gain / 20)
    for name, with_music in (("mix.wav", True), ("mix-nomusic.wav", False)):
        total = vo + game
        if with_music:
            total[:len(music)] += music
        sf.write(work / name, np.clip(total, -.98, .98), RATE)
    (work / "music-raw.wav").unlink()
    return {"bed_gain_db": round(gain, 2), "game_gain_db": round(20 * math.log10(vpk / gpk) - 12, 2), "speech_spans": len(speech)}


def subtitles(spec: dict, beats: list[dict], seconds: float) -> list[dict]:
    words = [{"w": w["w"], "s": b["from"] / FPS + w["s"], "e": b["from"] / FPS + w["e"]} for b in beats for w in b["words"]]
    subs = series.subtitle_groups(words, spec.get("emphasis", []), SUB["min_words"], SUB["max_words"])
    subs[-1]["e"] = min(subs[-1]["e"], seconds)
    return subs


def ig_previews(video: Path, beats: list[dict], qa: Path, caption: str) -> list[dict]:
    by = {b["id"]: b for b in beats}
    end = lambda k, d=4: (by[k]["from"] + by[k]["frames"] - d) / FPS
    pick = [("hook-0.5s", .5), ("hook-end", end("hook")), ("prompt", (by["idea"]["prompt"]["out"] - 4) / FPS), ("idea-reveal", end("idea")),
            ("build", (by["build"]["from"] + 40) / FPS), ("features-label", end("features", 10)), ("before-after", end("iteration")),
            ("result", end("result")), ("cta", end("cta", 3))]
    d = qa / "instagram"
    d.mkdir(parents=True, exist_ok=True)
    out = []
    for label, t in pick:
        for guides in (False, True):
            f = d / f"{label}{'-guides' if guides else ''}.png"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-vf",
                            br.ig_overlay_filter(guides, caption), str(f)], check=True, timeout=120)
        out.append({"label": label, "t": round(t, 2), "file": f"qa/instagram/{label}-guides.png"})
    inputs = sum([["-i", str(d / f"{lab}-guides.png")] for lab, _ in pick], [])
    n = len(pick)
    filt = "".join(f"[{i}]scale=360:640[s{i}];" for i in range(n)) + "".join(f"[s{i}]" for i in range(n)) + f"xstack=inputs={n}:layout=" + "|".join(
        f"{(i % 5) * 360}_{(i // 5) * 640}" for i in range(n)) + ":fill=0x111114"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", filt, "-frames:v", "1", str(qa / "instagram-safe-preview.png")], check=True, timeout=120)
    return out


def script_markdown(spec: dict, beats: list[dict], wpm: float, words: int, seconds: float) -> str:
    lines = [f"# {spec['title']} · narration script", "",
             f"{seconds:.1f} s · {words} words · {wpm:.0f} wpm while speaking (Kokoro, measured) · 1080×1920 · 30 fps", "",
             "| Time | Beat | Narration | On screen | Footage (real gameplay) |", "|---|---|---|---|---|"]
    for b in beats:
        a, z = b["from"] / FPS, (b["from"] + b["frames"]) / FPS
        txt = []
        if b.get("headline"):
            txt.append(" / ".join(b["headline"]["lines"]))
        txt += [x["text"] for x in b.get("label", [])]
        if b.get("pill"):
            txt.append(b["pill"]["text"])
        if b.get("prompt"):
            txt.append(f"{b['prompt']['label']}: “{' … '.join(b['prompt']['lines'])}”")
        if b.get("split"):
            txt.append(f"{b['split']['left']['label']} vs {b['split']['right']['label']} ({b['split']['note']})")
        if b.get("cta"):
            txt += [b["cta"]["big"], b["cta"]["small"], b["cta"]["handle"]]
        foot = [f"{s['clip']} @ {s['src']:.2f}s" for s in b["segs"]] or [f"{b['split']['left']['clip']} | {b['split']['right']['clip']} @ {b['split']['left']['src']:.2f}s"]
        lines.append(f"| {a:.1f}–{z:.1f} s | {b['id']} | {b['narration']} | {'<br>'.join(txt) or '—'} | {', '.join(foot)} |")
    lines += ["", "## Clips", ""] + [f"- **{k}**: {v}" for k, v in spec["clips"].items()]
    lines += ["", "## Claims and where they come from", ""] + [f"- **{k}**: {v}" for k, v in spec["claims"].items()]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", type=Path)
    ap.add_argument("--clips", type=Path, default=ROOT / "data" / "game-reel" / "clips", help="the recordings' audio (<clip>.wav, 24 kHz mono)")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--reuse-voice", action="store_true")
    ap.add_argument("--skip-render", action="store_true")
    ap.add_argument("--qa-only", action="store_true")
    a = ap.parse_args()
    started = time.time()
    spec = json.loads(a.spec.read_text())
    rid = spec["id"]
    out = a.out or ROOT / "outputs" / "reels" / rid
    work = ROOT / "data" / "game-reel" / rid
    (out / "qa").mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    missing = [c for c in spec["clips"] if not (ROOT / "public" / "game-reel" / f"{c}.mp4").exists() or not (a.clips / f"{c}.wav").exists()]
    if missing:
        raise SystemExit("missing recordings: " + ", ".join(missing))

    story = story_of(spec)
    cfg = {"pacing": {"wpm_target": spec["pacing"]["wpm_target"]}, "pronounce": {**bi.PRONOUNCE, **spec.get("pronounce", {})}}
    vcfg = settings.load()
    key = hashlib.sha256(json.dumps([story["scenes"], story["voice_speed"], cfg], sort_keys=True).encode()).hexdigest()[:16]
    cache = work / "voice.json"
    if a.reuse_voice and cache.exists() and json.loads(cache.read_text()).get("key") == key:
        voice = json.loads(cache.read_text())["voice"]
    else:
        voice = be.fit_voice(story, vcfg, work, cfg)
        cache.write_text(json.dumps({"key": key, "voice": voice}))
    timed = bi.timeline(story, voice)
    beats = resolve(spec, timed)
    frames = sum(b["frames"] for b in beats)
    seconds = frames / FPS
    subs = subtitles(spec, beats, seconds)
    info = mix(beats, voice, a.clips, seconds, work)
    vo = np.zeros(math.ceil(seconds * RATE), np.float32)
    for b, v in zip(beats, voice):
        fx._mix(vo, sf.read(v["wav"], dtype="float32")[0], b["from"] / FPS + b["lead_s"])
    props = {"fps": FPS, "durationInFrames": frames, "beats": beats, "subtitles": subs, "mouth": fx.mouth_envelope(vo, FPS)}
    (work / "props.json").write_text(json.dumps(props))
    print(json.dumps({"seconds": round(seconds, 2), "beats": [(b["id"], b["from"], b["frames"], round(b["speech_s"], 2)) for b in beats], **info}))
    if a.skip_render:
        return
    name = rid
    final, nomusic = out / f"{name}-final.mp4", out / f"{name}-no-music.mp4"
    cover_spec = spec["cover"]
    if not a.qa_only:
        print("render…")
        silent = work / "silent.mp4"
        bi.remotion("GameReel", silent, work / "props.json", vcfg)
        loud = {"final": be.master_tp(silent, work / "mix.wav", final), "no_music": be.master_tp(silent, work / "mix-nomusic.wav", nomusic)}
        (work / "loudness.json").write_text(json.dumps(loud))
        frame_png = ROOT / "public" / "game-reel" / "cover-frame.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(cover_spec["frame_t"]), "-i", str(ROOT / "public" / "game-reel" / f"{cover_spec['frame_clip']}.mp4"),
                        "-frames:v", "1", str(frame_png)], check=True)
        cp = {"frame": "game-reel/cover-frame.png", "crop": cover_spec["crop"], "lines": cover_spec["lines"], "accent": cover_spec["accent"],
              "tag": cover_spec["tag"], "handle": cover_spec["handle"]}
        (work / "cover.json").write_text(json.dumps(cp))
        bi.remotion("GameReelCover", out / f"{name}-cover.png", work / "cover.json", vcfg, still=0)
        be.cover_crops(out / f"{name}-cover.png", out / f"{name}-cover-4x5.png", out / f"{name}-cover-square.png")
        (work / "cover-mask.json").write_text(json.dumps({**cp, "mask": True}))
        bi.remotion("GameReelCover", out / "qa" / "cover-mask.png", work / "cover-mask.json", vcfg, still=0)
        be.grid_preview(out / f"{name}-cover-square.png", out / "qa" / "cover-grid-thumbnail.png")
        bi.contact_sheet(final, out / "qa" / "contact-sheet.png", seconds)
        (work / "props-guides.json").write_text(json.dumps({**props, "safeGuides": True}))
        first_line = (ROOT / "reels" / rid / "caption.md").read_text().split("\n")[0]
        caption_first = "".join(ch for ch in first_line if ch.isascii() and ch not in "':").strip()[:44]   # drawtext font has no emoji
        ig_previews(final, beats, out / "qa", caption_first + "…")
    loud = json.loads((work / "loudness.json").read_text())
    total_words = sum(len(b["words"]) for b in beats)
    wpm = 60 * total_words / sum(b["speech_s"] for b in beats)
    for f in ("caption.md", "prompt.md"):
        shutil.copy(ROOT / "reels" / rid / f, out / f"{name}-{f}")
    (out / f"{name}-script.md").write_text(script_markdown(spec, beats, wpm, total_words, seconds))
    import qa_game_reel
    report = qa_game_reel.run(out, name, props, spec, loud, voice, wpm)
    meta = {"id": rid, "title": spec["title"], "seconds": round(seconds, 2), "frames": frames, "wpm": round(wpm, 1), "words": total_words,
            "voice": {"engine": voice[0]["engine"], "voice": voice[0]["voice"], "speed": voice[0]["speed"], "speed_search": voice[0].get("speed_search")},
            "loudness": loud, "mix": info, "source": spec["source"], "beats": [{"id": b["id"], "from_s": round(b["from"] / FPS, 2), "seconds": round(b["frames"] / FPS, 2),
            "narration": b["narration"], "cuts": [{k: s[k] for k in ("clip", "src", "frames")} for s in b["segs"]]} for b in beats],
            "files": sorted(p.name for p in out.iterdir() if p.is_file()), "qa_summary": report["summary"], "build_seconds": round(time.time() - started)}
    (out / f"{name}-metadata.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    (out / f"{name}-qa-report.md").write_text(qa_game_reel.markdown(report, meta))
    print(json.dumps(report["summary"], indent=1))


if __name__ == "__main__":
    main()
