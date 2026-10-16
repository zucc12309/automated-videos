"""Narration engines. Kokoro stays the default; espeak-ng is a local, clearly lower-quality fallback.

Both return the same Narration record so the rest of the pipeline does not care which voice spoke.
"""
from __future__ import annotations

import math
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import alignment, audio as audio_fx

RATE = 24000
_KOKORO = {}

ACRONYMS = {"MCP": "M C P", "LLM": "L L M", "API": "A P I", "CLI": "C L I", "SDK": "S D K", "UI": "U I", "YC": "Y C",
            "GPU": "G P U", "CPU": "C P U", "JSON": "jason", "YAML": "yamel", "SQL": "sequel", "README": "read me",
            "npm": "N P M", "repo": "repo", "repos": "repos", "AI": "A I", "IDE": "I D E", "PR": "P R", "PRs": "P Rs"}


@dataclass
class Narration:
    audio: np.ndarray
    words: list[dict]
    visemes: list[list]
    engine: str
    voice: str
    timing_source: str
    notes: list[str] = field(default_factory=list)


def spoken_form(text: str, pronunciations: dict[str, str], expand_acronyms: bool, engine: str) -> list[tuple[str, str]]:
    """[(caption_word, spoken_word)] — captions always show the original word."""
    out = []
    for word in text.split():
        core = word.strip(".,!?;:'\"()")
        spoken = pronunciations.get(core) or pronunciations.get(core.lower())
        if spoken is None and expand_acronyms and engine == "espeak":
            spoken = ACRONYMS.get(core)
        out.append((word, word.replace(core, spoken) if spoken and core else word))
    return out


def available_engine(preferred: str) -> tuple[str, str]:
    """Resolve 'auto' to a usable engine and say why."""
    kokoro_ok, why = False, ""
    try:
        import kokoro  # noqa: F401
        kokoro_ok = True
    except Exception as exc:
        why = f"kokoro not importable ({type(exc).__name__})"
    if preferred == "kokoro":
        return "kokoro", "configured"
    if preferred == "espeak":
        return "espeak", "configured"
    if kokoro_ok:
        return "kokoro", "default"
    if shutil.which("espeak-ng"):
        return "espeak", f"fallback: {why}"
    raise RuntimeError(f"No narration engine: {why}; install Kokoro (pip) or espeak-ng")


def _kokoro(cfg) -> object:
    from kokoro import KPipeline
    key = cfg.tts_language_code
    if key not in _KOKORO:
        _KOKORO[key] = KPipeline(lang_code=key, repo_id="hexgrad/Kokoro-82M", device="cpu")
    return _KOKORO[key]


def kokoro_narrate(text: str, cfg, fps: int) -> Narration:
    pairs = spoken_form(text, cfg.narration.pronunciations, False, "kokoro")
    spoken = " ".join(s for _, s in pairs)
    results = list(_kokoro(cfg)(spoken, voice=cfg.voice, speed=cfg.voice_speed))
    if not results:
        raise RuntimeError("Kokoro returned no audio")
    audio = np.concatenate([r.audio.numpy() for r in results]).astype(np.float32)
    words = alignment.retarget(audio_fx.word_timings(results), [c for c, _ in pairs])
    return Narration(audio, words, audio_fx.visemes(results, fps), "kokoro", cfg.voice, "kokoro_timestamps")


GRAPHEME = [("th", "H"), ("oo", "F"), ("ee", "B"), ("ch", "B"), ("sh", "B"), ("m", "A"), ("b", "A"), ("p", "A"), ("f", "G"),
            ("v", "G"), ("l", "H"), ("w", "F"), ("o", "E"), ("u", "F"), ("a", "D"), ("e", "C"), ("i", "C"), ("y", "B")]


def text_visemes(words: list[dict], fps: int) -> list[list]:
    """Approximate mouth shapes from spelling, for engines without phoneme timestamps."""
    cues = []
    for w in words:
        letters = re.sub(r"[^a-z]", "", w["w"].lower())
        units, i = [], 0
        while i < len(letters):
            for g, shape in GRAPHEME:
                if letters.startswith(g, i):
                    units.append(shape)
                    i += len(g)
                    break
            else:
                units.append("B")
                i += 1
        units = units or ["C"]
        step = (w["e"] - w["s"]) / len(units)
        for k, shape in enumerate(units):
            cues.append((w["s"] + k * step - .05, shape))
        cues.append((w["e"], "X"))
    frames: list[list] = []
    for t, shape in sorted(cues):
        frame = max(0, round(t * fps))
        if frames and frame - frames[-1][0] < 2:
            continue
        if not frames or frames[-1][1] != shape:
            frames.append([frame, shape])
    return frames


def espeak_narrate(text: str, cfg, fps: int) -> Narration:
    """Synthesize phrase by phrase so phrase boundaries are exact; estimate + energy-snap words inside each phrase."""
    binary = shutil.which("espeak-ng")
    if not binary:
        raise RuntimeError("espeak-ng is not installed")
    pairs = spoken_form(text, cfg.narration.pronunciations, cfg.narration.expand_acronyms, "espeak")
    phrases, current = [], []
    for caption, spoken in pairs:
        current.append((caption, spoken))
        if re.search(r"[.,!?;:—]$", caption):
            phrases.append(current)
            current = []
    if current:
        phrases.append(current)
    wpm = int(165 * cfg.voice_speed)
    chunks, words, t = [], [], 0.0
    with tempfile.TemporaryDirectory() as tmp:
        for i, phrase in enumerate(phrases):
            out = Path(tmp) / f"p{i}.wav"
            subprocess.run([binary, "-v", cfg.narration.espeak_voice, "-s", str(wpm), "-w", str(out), " ".join(s for _, s in phrase)],
                           check=True, capture_output=True, timeout=60)
            pcm = _read_resampled(out)
            pcm = _trim(pcm)
            gap = .18 if re.search(r"[.!?]$", phrase[-1][0]) else .08
            est = alignment.estimate([c for c, _ in phrase], 0, len(pcm) / RATE)
            est = alignment.energy_snap(pcm, RATE, est)
            words += [{"w": w["w"], "s": round(w["s"] + t, 3), "e": round(w["e"] + t, 3)} for w in est]
            chunks += [pcm, np.zeros(int(gap * RATE), dtype=np.float32)]
            t += len(pcm) / RATE + gap
    audio = np.concatenate(chunks[:-1]) if len(chunks) > 1 else chunks[0]
    return Narration(audio, words, text_visemes(words, fps), "espeak", cfg.narration.espeak_voice, "energy_snapped",
                     ["espeak-ng fallback voice: robotic timbre; install Kokoro for production narration"])


def _read_resampled(path: Path) -> np.ndarray:
    import soundfile as sf
    data, rate = sf.read(path, dtype="float32")
    if data.ndim > 1:
        data = data.mean(axis=1)
    if rate != RATE:
        n = math.ceil(len(data) * RATE / rate)
        data = np.interp(np.linspace(0, len(data) - 1, n), np.arange(len(data)), data).astype(np.float32)
    return data


def _trim(pcm: np.ndarray, threshold: float = .01) -> np.ndarray:
    idx = np.where(np.abs(pcm) > threshold)[0]
    if len(idx) == 0:
        return pcm
    return pcm[max(0, idx[0] - 240):min(len(pcm), idx[-1] + 480)]


def narrate(text: str, cfg, fps: int, engine: str) -> Narration:
    result = kokoro_narrate(text, cfg, fps) if engine == "kokoro" else espeak_narrate(text, cfg, fps)
    if not np.isfinite(result.audio).all() or np.max(np.abs(result.audio)) < 0.001:
        raise RuntimeError("Speech synthesis returned invalid or silent audio")
    return result
