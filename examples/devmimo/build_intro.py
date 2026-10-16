"""DevMimo intro (30 s) and logo sting (5 s), built on the existing V2.2 pieces.

Reused, not rebuilt:
- Kokoro narration (`tts.narrate`, am_adam via kokoro-onnx);
- the reference voice EQ (`audio_profile.match_eq`);
- the procedural SFX palette and warm-pad bed (`audio`);
- the reference bed level (`audio_profile.bed_gain_db`);
- the linear -14 LUFS master;
- the Remotion CLI.

New here: the DevMimo compositions in `src/devmimo/`. This script times them to the real narration and mixes the sound to the same
frames.

    .venv/bin/python examples/devmimo/build_intro.py            # narrate, mix, render both, QA
    .venv/bin/python examples/devmimo/build_intro.py --skip-render  # narration + props + audio only
"""
from __future__ import annotations

import argparse
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
sys.path.insert(0, str(ROOT))

from video_mcp import audio as fx, audio_profile, settings, tts  # noqa: E402
from video_mcp.audio import RATE  # noqa: E402

FPS = 30
TARGET_S = 26.0          # Instagram pacing pass (was 30 s); overridable by storyboard pacing.target_s
OUT = ROOT / "demos" / "devmimo"
WORK = ROOT / "data" / "devmimo"
HERE = Path(__file__).resolve().parent

# Spoken forms only; on-screen text always shows the written word.
PRONOUNCE = {"Mimo": "Meemo", "DevMimo": "Dev Meemo", "MCP": "M C P"}


def board() -> dict:
    return json.loads((HERE / "devmimo_intro_storyboard.json").read_text())


# ---------------------------------------------------------------- narration
def narrate(story: dict, cfg, work: Path = WORK, pronounce: dict | None = None) -> list[dict]:
    engine, why = tts.available_engine("auto")
    if not engine.startswith("kokoro"):
        raise SystemExit(f"Kokoro is required for the DevMimo voice; resolved engine {engine!r}: {why}")
    cfg.narration.pronunciations = {**cfg.narration.pronunciations, **(PRONOUNCE if pronounce is None else pronounce)}
    cfg.voice_speed = story.get("voice_speed", cfg.voice_speed)
    prof = audio_profile.profile()
    strength = prof["targets"]["narration_eq"].get("kokoro_strength", .5)
    work.mkdir(parents=True, exist_ok=True)
    out = []
    for i, scene in enumerate(story["scenes"]):
        n = tts.narrate(scene["narration"], cfg, FPS, engine)
        raw, wav = work / f"vo-{i}-raw.wav", work / f"vo-{i}.wav"
        sf.write(raw, n.audio, RATE)
        eq, eq_info = audio_profile.match_eq(n.audio, RATE, prof["measured"]["voice_bands_db"], strength)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af",
                        "highpass=f=75," + (eq + "," if eq else "") +
                        "acompressor=threshold=-20dB:ratio=2.5:attack=5:release=80,loudnorm=I=-16:TP=-1.5:LRA=7",
                        "-ar", str(RATE), "-ac", "1", str(wav)], check=True, timeout=300)
        raw.unlink()
        pcm, _ = sf.read(wav, dtype="float32")
        out.append({"id": scene["id"], "engine": n.engine, "voice": n.voice, "timing_source": n.timing_source, "eq": eq_info,
                    "seconds": round(len(pcm) / RATE, 3), "words": n.words, "wav": str(wav)})
        print(f"  {scene['id']}: {len(pcm) / RATE:.2f}s  {scene['narration']}")
    return out


# ---------------------------------------------------------------- timing
def timeline(story: dict, voice: list[dict]) -> list[dict]:
    """Scene length = lead-in + speech + tail. Tails share whatever is left of the 30 s by each scene's `hold` weight, so the
    picture always waits for the voice and the total lands on the target."""
    base = [s.get("lead_s", .1) + v["seconds"] + s.get("min_tail_s", .25) for s, v in zip(story["scenes"], voice)]
    target = story.get("pacing", {}).get("target_s", TARGET_S)
    spare = target - sum(base)
    if spare < 0:
        print(f"  narration overruns {target}s by {-spare:.2f}s; tails stay at their minimum")
        spare = 0
    weights = [s.get("hold", 1) for s in story["scenes"]]
    if sum(weights) <= 0:
        weights = [1] * len(weights)
    out, t = [], 0
    for s, v, b, w in zip(story["scenes"], voice, base, weights):
        frames = round((b + spare * w / sum(weights)) * FPS)
        lead = s.get("lead_s", .1)
        words = [{"w": x["w"], "s": round(x["s"] + lead, 3), "e": round(x["e"] + lead, 3)} for x in v["words"]]
        out.append({"id": s["id"], "kind": s["kind"], "from": t, "frames": frames, "lead_s": lead, "speech_s": v["seconds"],
                    "words": words, "text": s.get("on_screen", {})})
        t += frames
    return out


# ---------------------------------------------------------------- sound
def boom() -> np.ndarray:
    """Low sub impact for the mascot reveal."""
    t = np.arange(round(1.4 * RATE), dtype=np.float32) / RATE
    body = np.sin(2 * np.pi * np.cumsum(np.linspace(78, 34, len(t))) / RATE) * np.exp(-t * 3.2)
    click = fx._tone(.02, 1600, 600, 160)
    out = body.astype(np.float32)
    fx._mix(out, click, 0, .35)
    return out


def riser(seconds: float) -> np.ndarray:
    n = fx._noise(seconds)
    env = np.linspace(0, 1, len(n)) ** 2.4
    return fx._lowpass(n * env, np.linspace(300, 7000, len(n))) * .45


def key_clicks(seconds: float, rate_hz: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    track = fx._blank(seconds)
    t = 0.0
    while t < seconds:
        fx._mix(track, fx._tone(.018, 2600 + rng.uniform(-400, 400), 1500, 260), t, .22 + rng.uniform(0, .1))
        t += rng.uniform(.6, 1.4) / rate_hz
    return track


def glitch() -> np.ndarray:
    n = fx._noise(.22)
    gate = (np.sin(np.arange(len(n)) / RATE * 2 * np.pi * 38) > 0).astype(np.float32)
    return (n * gate * np.exp(-np.arange(len(n)) / RATE * 9) * .35).astype(np.float32)


def sfx_track(scenes: list[dict], cues: list[dict], seconds: float) -> np.ndarray:
    """Every cue is placed on a frame the components also use (storyboard `sfx` list, frame offsets inside the scene)."""
    track = fx._blank(seconds)
    sounds = {"whoosh": fx.whoosh, "pop": fx.pop, "tick": fx.tick, "chime": fx.chime, "stamp": fx.stamp, "plug": fx.plug,
              "boom": boom, "glitch": glitch}
    by_id = {s["id"]: s for s in scenes}
    for cue in cues:
        s = by_id[cue["scene"]]
        word = s["words"][cue["word"]]["s"] if "word" in cue else 0.0   # word-anchored cues follow the real narration
        at = (s["from"] + cue["frame"]) / FPS + word
        if cue["sound"] == "riser":
            r = riser(cue.get("seconds", 1.0))
            fx._mix(track, r, at - len(r) / RATE, cue.get("gain", .5))
        elif cue["sound"] == "keys":
            fx._mix(track, key_clicks(cue.get("seconds", 1.0), cue.get("rate", 14), cue["frame"]), at, cue.get("gain", .5))
        else:
            fx._mix(track, sounds[cue["sound"]](), at, cue.get("gain", .5))
    return track


def mix(scenes: list[dict], voice: list[dict], cues: list[dict], seconds: float, work: Path = WORK, music_on: bool = True,
        out_name: str = "mix.wav") -> dict:
    n = math.ceil(seconds * RATE)
    vo = np.zeros(n, np.float32)
    speech, voices = [], []
    for s, v in zip(scenes, voice):
        pcm, _ = sf.read(v["wav"], dtype="float32")
        voices.append(pcm)
        at = s["from"] / FPS + s["lead_s"]
        fx._mix(vo, pcm, at)
        speech += [(s["from"] / FPS + w["s"], s["from"] / FPS + w["e"]) for w in s["words"]]
    prof = audio_profile.profile()
    bed_cfg = prof["targets"]["music"]
    fx.music_bed(work / "music-raw.wav", seconds, 84, 2, speech, style=bed_cfg.get("style", "warm_pad"), duck_db=bed_cfg.get("duck_db", -6))
    music, _ = sf.read(work / "music-raw.wav", dtype="float32")
    gain = audio_profile.bed_gain_db(voices, music, RATE, prof["measured"]["bed_minus_speech_db"])
    music = music[:n] * 10 ** (gain / 20)
    sfx = sfx_track(scenes, cues, seconds)[:n]
    # SFX sit under the voice: measured against the narration peak, not absolute.
    sfx *= 10 ** (-9 / 20)
    total = vo.copy()
    if music_on:                                  # the no-music export keeps voice + SFX at the same levels
        total[:len(music)] += music
    total[:len(sfx)] += sfx
    sf.write(work / out_name, np.clip(total, -.98, .98), RATE)
    (work / "music-raw.wav").unlink()
    return {"bed_gain_db": gain, "speech_spans": len(speech)}


def logo_audio(seconds: float) -> Path:
    track = fx._blank(seconds)
    fx._mix(track, riser(.8), 0.0, .35)
    for f, s, g in [(14, fx.pop, .45), (22, fx.pop, .45), (34, boom, .7), (40, fx.whoosh, .35), (58, fx.tick, .4), (64, fx.tick, .4),
                    (70, fx.tick, .4), (76, fx.tick, .4), (96, fx.chime, .35), (112, fx.pop, .25)]:
        fx._mix(track, s(), f / FPS, g)
    pad = fx.warm_pad(seconds, 84, 2)[:len(track)] * .55
    fade = RATE
    pad[:fade] *= np.linspace(0, 1, fade)
    pad[-fade:] *= np.linspace(1, 0, fade)
    track += pad
    path = WORK / "logo-mix.wav"
    sf.write(path, np.clip(track, -.98, .98), RATE)
    return path


# ---------------------------------------------------------------- render + master
def remotion(comp: str, out: Path, props: Path | None, cfg, extra: list[str] | None = None, still: int | None = None):
    cli = ROOT / "node_modules" / ".bin" / "remotion"
    args = [str(cli), "still" if still is not None else "render", "src/index.tsx", comp, str(out), "--log=error"]
    if props:
        args.append(f"--props={props}")
    if still is not None:
        args.append(f"--frame={still}")
    else:
        args += ["--codec=h264", "--crf=16", "--concurrency=4", "--muted"]
    if cfg.browser():
        args.append(f"--browser-executable={cfg.browser()}")
    subprocess.run(args + (extra or []), cwd=ROOT, check=True, timeout=3600, stdout=subprocess.DEVNULL)


def master(silent: Path, wav: Path, out: Path, lufs: float = -14.0):
    """Linear gain to the target (keeps the pauses' dynamics), limiter, AAC. The limiter shaves the SFX peaks, which lowers the
    integrated loudness, so the gain is re-measured and corrected (up to 3 passes); true peak is corrected after encoding."""
    gain, limit = lufs - audio_profile.loudness(wav)["integrated_lufs"], .84
    for _ in range(5):
        chain = f"volume={gain:.2f}dB,alimiter=limit={limit:.3f}:attack=1:release=60:level=false"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(silent), "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                        "-af", chain, "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)], check=True, timeout=600)
        m = audio_profile.loudness(out)
        if abs(m["integrated_lufs"] - lufs) <= .3 and m["true_peak_dbtp"] <= -1.0:
            return m
        if m["true_peak_dbtp"] > -1.0:          # AAC overshoot: lower the ceiling, keep the loudness
            limit *= 10 ** ((-1.25 - m["true_peak_dbtp"]) / 20)
        gain += lufs - m["integrated_lufs"]
    return m


def contact_sheet(video: Path, out: Path, seconds: float, cols: int = 6, rows: int = 4):
    n = cols * rows
    rate = n / seconds
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vf",
                    f"fps={rate:.5f},scale=270:-1,drawtext=text='%{{pts\\:hms}}':x=8:y=8:fontcolor=white:fontsize=18:box=1:boxcolor=black@0.6,"
                    f"tile={cols}x{rows}:padding=6:margin=6:color=0x111114", "-frames:v", "1", str(out)], check=True, timeout=300)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-render", action="store_true")
    ap.add_argument("--reuse-voice", action="store_true", help="reuse data/devmimo narration if present")
    a = ap.parse_args()
    cfg = settings.load()
    story = board()
    started = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    cache = WORK / "voice.json"
    if a.reuse_voice and cache.exists():
        voice = json.loads(cache.read_text())
    else:
        print("narration (Kokoro):")
        voice = narrate(story, cfg)
        cache.write_text(json.dumps(voice))
    scenes = timeline(story, voice)
    frames = sum(s["frames"] for s in scenes)
    seconds = frames / FPS
    info = mix(scenes, voice, story["sfx"], seconds)
    props = {"fps": FPS, "durationInFrames": frames, "scenes": scenes, "mouth": [], "handle": story.get("handle")}
    # Mimo speaks the narration: one mouth value per frame from the mixed voice only.
    vo = np.zeros(math.ceil(seconds * RATE), np.float32)
    for s, v in zip(scenes, voice):
        pcm, _ = sf.read(v["wav"], dtype="float32")
        fx._mix(vo, pcm, s["from"] / FPS + s["lead_s"])
    props["mouth"] = fx.mouth_envelope(vo, FPS)
    (WORK / "props.json").write_text(json.dumps(props))
    shutil.copy(HERE / "devmimo_intro_storyboard.json", OUT / "devmimo_intro_storyboard.json")
    timing = {"target_s": story.get("pacing", {}).get("target_s", TARGET_S), "seconds": round(seconds, 3), "frames": frames,
              "scenes": [{"id": s["id"], "from": s["from"], "frames": s["frames"], "speech_s": s["speech_s"]} for s in scenes],
              "voice": {"engine": voice[0]["engine"], "voice": voice[0]["voice"]}, **info}
    (WORK / "timing.json").write_text(json.dumps(timing, indent=1))
    print(json.dumps(timing, indent=1))
    if a.skip_render:
        return
    print("render intro…")
    silent = WORK / "intro-silent.mp4"
    remotion("DevMimoIntro", silent, WORK / "props.json", cfg)
    master(silent, WORK / "mix.wav", OUT / "devmimo_intro.mp4")
    remotion("DevMimoPoster", OUT / "devmimo_intro_poster.png", None, cfg, still=0)
    contact_sheet(OUT / "devmimo_intro.mp4", OUT / "devmimo_intro_contact_sheet.png", seconds)
    print("render logo…")
    remotion("DevMimoLogo", WORK / "logo-silent.mp4", None, cfg)
    master(WORK / "logo-silent.mp4", logo_audio(5.0), OUT / "devmimo_logo.mp4", lufs=-16.0)
    contact_sheet(OUT / "devmimo_logo.mp4", OUT / "devmimo_logo_contact_sheet.png", 5.0, cols=5, rows=2)
    sys.path.insert(0, str(HERE))
    import qa
    report = qa.run(OUT / "devmimo_intro.mp4", OUT / "devmimo_logo.mp4", props, story, timing)
    report["build_seconds"] = round(time.time() - started, 1)
    (OUT / "devmimo_intro_qa.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report["summary"], indent=1))


if __name__ == "__main__":
    main()
