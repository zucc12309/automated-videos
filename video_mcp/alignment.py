"""Word timing for narration.

Sources, best first (recorded per job as `alignment.source`):
  kokoro_timestamps   Kokoro's own per-token timestamps (model-derived; what the studio style always used)
  energy_snapped      phrase-anchored estimate refined by snapping word boundaries to local energy minima
  estimated           syllable-weighted estimate inside known phrase boundaries

Heavier forced aligners (WhisperX, MFA, ctc-forced-aligner) were evaluated; see docs/QUALITY_ASSURANCE.md. They need
large model downloads (and MFA a conda environment), so they are optional plug-ins, not dependencies.
"""
from __future__ import annotations

import re

import numpy as np

VOWELS = re.compile(r"[aeiouy]+")


def syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        digits = re.sub(r"\D", "", word)
        return max(1, len(digits))           # numbers are spoken long
    count = len(VOWELS.findall(w))
    if w.endswith("e") and count > 1 and not w.endswith(("le", "ee")):
        count -= 1
    if w.isupper() or (len(w) <= 4 and not VOWELS.search(w)):
        count = len(w)                        # acronyms are spelled out
    return max(1, count)


def estimate(words: list[str], start: float, end: float) -> list[dict]:
    weights = [syllables(w) + (0.6 if re.search(r"[,;:]$", w) else 0) for w in words]
    total = sum(weights) or 1
    out, t = [], start
    for word, weight in zip(words, weights):
        length = (end - start) * weight / total
        out.append({"w": word, "s": round(t, 3), "e": round(t + length * .92, 3)})
        t += length
    return out


def envelope(audio: np.ndarray, rate: int, hop: float = .01) -> np.ndarray:
    n = max(1, int(rate * hop))
    frames = len(audio) // n
    if frames == 0:
        return np.zeros(1, dtype=np.float32)
    trimmed = audio[:frames * n].reshape(frames, n)
    return np.sqrt((trimmed.astype(np.float32) ** 2).mean(axis=1))


def energy_snap(audio: np.ndarray, rate: int, words: list[dict], window: float = .12, hop: float = .01) -> list[dict]:
    """Move each internal word boundary to the quietest 10 ms frame within ±window, keeping order and a 60 ms minimum."""
    if len(words) < 2:
        return words
    env = envelope(audio, rate, hop)
    out = [dict(w) for w in words]
    for i in range(1, len(out)):
        boundary = out[i]["s"]
        lo, hi = int((boundary - window) / hop), int((boundary + window) / hop)
        lo, hi = max(lo, int((out[i - 1]["s"] + .06) / hop)), min(hi, len(env) - 1)
        if i + 1 < len(out):
            hi = min(hi, int((out[i + 1]["s"] - .06) / hop))
        if hi <= lo:
            continue
        k = lo + int(np.argmin(env[lo:hi + 1]))
        out[i]["s"] = round(k * hop, 3)
    for i in range(len(out) - 1):
        out[i]["e"] = round(min(max(out[i]["e"], out[i]["s"] + .05), out[i + 1]["s"]), 3)
    out[-1]["e"] = round(max(out[-1]["e"], out[-1]["s"] + .05), 3)
    return out


def retarget(spoken: list[dict], original: list[str]) -> list[dict]:
    """Map timings of the spoken token sequence onto the caption's original words (pronunciation edits change tokens)."""
    if not spoken:
        return []
    if len(spoken) == len(original):
        return [{"w": o, "s": s["s"], "e": s["e"]} for o, s in zip(original, spoken)]
    start, end = spoken[0]["s"], spoken[-1]["e"]
    return estimate(original, start, end)


def sync_error(words: list[dict], audio: np.ndarray, rate: int) -> dict:
    """QA: how far captions sit from the speech they label. Measures speech energy inside vs outside word spans."""
    env = envelope(audio, rate)
    if env.max() <= 0 or not words:
        return {"inside_ratio": 0.0, "covered_speech": 0.0}
    active = env > env.max() * .08
    inside = np.zeros_like(active)
    for w in words:
        inside[int(w["s"] / .01):int(w["e"] / .01) + 1] = True
    covered = (active & inside).sum() / max(1, active.sum())
    precision = (active & inside).sum() / max(1, inside.sum())
    return {"covered_speech": round(float(covered), 3), "inside_ratio": round(float(precision), 3)}
