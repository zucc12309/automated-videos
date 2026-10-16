"""Procedural sound design, lip-sync envelopes and word timings. Everything is generated locally."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import soundfile as sf

RATE = 24000
_rng = np.random.default_rng(7)

# Seconds after a scene starts; keep in sync with the timings in src/paper/*.tsx.
CARD_AT, PLUG_AT, STAMP_AT, COUNT_FROM, COUNT_TO = 0.15, 0.73, 1.0, 0.35, 1.8


def _blank(seconds: float) -> np.ndarray:
    return np.zeros(max(1, math.ceil(seconds * RATE)), dtype=np.float32)


def _mix(track: np.ndarray, sound: np.ndarray, at: float, gain: float = 1.0):
    begin = round(at * RATE)
    count = min(len(sound), len(track) - begin)
    if count > 0 and begin >= 0:
        track[begin:begin + count] += sound[:count] * gain


def _tone(seconds: float, f0: float, f1: float, decay: float) -> np.ndarray:
    t = np.arange(round(seconds * RATE), dtype=np.float32) / RATE
    phase = 2 * np.pi * np.cumsum(np.linspace(f0, f1, len(t), dtype=np.float32)) / RATE
    return (np.sin(phase) * np.exp(-t * decay)).astype(np.float32)


def _noise(seconds: float) -> np.ndarray:
    return _rng.standard_normal(round(seconds * RATE)).astype(np.float32)


def _lowpass(x: np.ndarray, cutoff: np.ndarray | float) -> np.ndarray:
    alpha = np.broadcast_to(1 - np.exp(-2 * np.pi * np.asarray(cutoff, dtype=np.float32) / RATE), x.shape)
    out, acc = np.empty_like(x), 0.0
    for i in range(len(x)):
        acc += alpha[i] * (x[i] - acc)
        out[i] = acc
    return out


def whoosh() -> np.ndarray:
    n = _noise(.38)
    env = np.sin(np.linspace(0, np.pi, len(n))) ** 2
    return _lowpass(n * env, np.linspace(400, 5000, len(n))) * .5


def pop() -> np.ndarray:
    out = _tone(.09, 520, 980, 40) * .8
    _mix(out, _tone(.02, 3000, 2000, 200), 0, .2)
    return out


def plug() -> np.ndarray:
    click = _tone(.03, 2400, 1800, 160)
    thunk = _tone(.16, 170, 80, 26)
    out = np.zeros(round(.2 * RATE), dtype=np.float32)
    _mix(out, click, 0, .7)
    _mix(out, click, .055, .5)
    _mix(out, thunk, .05, .9)
    return out


def stamp() -> np.ndarray:
    n = _noise(.12)
    out = _tone(.22, 120, 60, 18)
    _mix(out, _lowpass(n * np.exp(-np.arange(len(n)) / RATE * 40), 1800), 0, .6)
    return out


def tick() -> np.ndarray:
    return _tone(.025, 1900, 1700, 220) * .5


def chime() -> np.ndarray:
    return sum(_tone(1.1, f, f, 3.5) * g for f, g in [(523.25, .5), (659.25, .4), (783.99, .35), (1046.5, .2)]).astype(np.float32)


def scene_sfx(path: Path, seconds: float, index: int, visual: str, item: int, has_stat: bool):
    track = _blank(seconds)
    if index > 0:
        _mix(track, whoosh(), 0, .55)
    _mix(track, pop(), CARD_AT, .35)
    if item > 0:
        _mix(track, plug(), PLUG_AT, .55)
    if visual == "doc" and item > 0:
        _mix(track, stamp(), STAMP_AT, .5)
    if has_stat or visual == "repo":
        for t in np.linspace(COUNT_FROM, COUNT_TO, 14) ** 1.0:
            _mix(track, tick(), float(t), .25)
    if visual == "outro":
        _mix(track, chime(), .3, .22)
    sf.write(path, np.clip(track, -.95, .95), RATE)


PROGRESSIONS = [
    [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [261.63, 329.63, 392.0], [196.0, 246.94, 293.66]],      # Am F C G
    [[146.83, 174.61, 220.0], [233.08, 293.66, 349.23], [174.61, 220.0, 261.63], [261.63, 329.63, 392.0]],     # Dm Bb F C
    [[261.63, 329.63, 392.0, 493.88], [220.0, 261.63, 329.63, 392.0], [174.61, 220.0, 261.63, 329.63], [196.0, 246.94, 293.66, 349.23]],  # Cmaj7 Am7 Fmaj7 G7
    [[164.81, 196.0, 246.94], [130.81, 164.81, 196.0], [196.0, 246.94, 293.66], [146.83, 185.0, 220.0]],       # Em C G D
]


def duck_curve(seconds: float, speech: list[tuple[float, float]], depth_db=-7.0, attack=.05, release=.4) -> np.ndarray:
    """Per-sample gain for the music: dips by depth_db while the voice speaks (computed offline from word timings)."""
    target = np.zeros(max(1, math.ceil(seconds * RATE)), dtype=np.float32)
    for start, end in speech:
        target[max(0, round(start * RATE)):round(end * RATE)] = 1
    hop = RATE // 100
    coarse = target[::hop].copy()
    out, level = np.empty_like(coarse), 0.0
    up, down = 1 - math.exp(-1 / (attack * 100)), 1 - math.exp(-1 / (release * 100))
    for k, v in enumerate(coarse):
        level += (up if v > level else down) * (v - level)
        out[k] = level
    gain = 10 ** (depth_db * np.repeat(out, hop)[:len(target)] / 20)
    return np.pad(gain, (0, len(target) - len(gain)), constant_values=1).astype(np.float32)


def beat_sfx(path: Path, seconds: float, beats: list[dict], words: list[dict], emphasis: str):
    """One job per sound: whoosh on moving transitions, pop on entrances, impact on the stressed word, stamp/ticks on payoffs."""
    track = _blank(seconds)
    for b, beat in enumerate(beats):
        at = beat["s"]
        if b or beat.get("transition") != "cut":
            if beat.get("transition") in ("whip", "push", "zoom", "mask"):
                _mix(track, whoosh(), max(0, at - .1), .45)
            else:
                _mix(track, pop(), at + .02, .3)
        layout = beat.get("layout")
        if layout == "docStamp":
            _mix(track, stamp(), at + STAMP_AT, .45)
        if layout in ("repoCard", "bigNumber", "starMeter"):
            for t in np.linspace(at + COUNT_FROM, at + min(COUNT_TO, beat["e"] - beat["s"]), 10):
                _mix(track, tick(), float(t), .22)
        if layout in ("loop", "recap"):
            _mix(track, chime(), at + .25, .16)
        if beat.get("punch") and emphasis:
            hit = next((w for w in words[beat["w"][0]:beat["w"][1] + 1] if emphasis.lower().split()[0] in w["w"].lower()), None)
            if hit:
                _mix(track, _tone(.18, 150, 55, 22), max(0, hit["s"] - .03), .5)
    sf.write(path, np.clip(track, -.95, .95), RATE)


def warm_pad(seconds: float, bpm: float, progression: int) -> np.ndarray:
    """Reference A's bed: a soft, low, slowly breathing pad (energy ~140-340 Hz), no drums or plucks.

    Chords sit in the 130-500 Hz register with a quiet root an octave below; upper partials are filtered away and long
    cross-fades join the chords."""
    bar = 60 / bpm * 4 * 2                    # two bars per chord: slow harmonic rhythm
    chords = PROGRESSIONS[progression % len(PROGRESSIONS)]
    track = _blank(seconds + bar)
    for b in range(math.ceil(seconds / bar) + 1):
        chord = chords[b % len(chords)]
        t = np.arange(round((bar + 1.2) * RATE), dtype=np.float32) / RATE
        pad = sum(np.sin(2 * np.pi * f * t + i) + .18 * np.sin(2 * np.pi * f * 2.002 * t) for i, f in enumerate(chord)) / len(chord)
        pad += .3 * np.sin(2 * np.pi * chord[0] / 2 * t)                       # soft root an octave below
        swell = 1 + .12 * np.sin(2 * np.pi * t / bar)
        env = np.minimum(1, t / 1.2) * np.minimum(1, (bar + 1.2 - t) / 1.2) * swell
        _mix(track, _lowpass((pad * env * .09).astype(np.float32), 900), b * bar)
    return track


def music_bed(path: Path, seconds: float, bpm: float = 92, progression: int = 0, speech: list[tuple[float, float]] | None = None,
              style: str = "lofi", duck_db: float = -7.0):
    """style "lofi": pad + soft kick/hat + plucked arpeggio (V2). style "warm_pad": Reference A's low pad (brand/audio_profile.json).
    Key, tempo and harmony vary per video. Ducked under speech."""
    if style == "warm_pad":
        track = warm_pad(seconds, bpm, progression)[:round(seconds * RATE)]
        if speech:
            track *= duck_curve(seconds, speech, depth_db=duck_db)[:len(track)]
        fade = min(len(track), RATE * 2)
        track[-fade:] *= np.linspace(1, 0, fade)
        sf.write(path, np.clip(track, -.95, .95), RATE)
        return
    beat = 60 / bpm
    track = _blank(seconds + 1)
    chords = PROGRESSIONS[progression % len(PROGRESSIONS)]
    bar = beat * 4
    for b in range(math.ceil(seconds / bar) + 1):
        chord = chords[b % len(chords)]
        t = np.arange(round(bar * RATE), dtype=np.float32) / RATE
        pad = sum(np.sin(2 * np.pi * f * t) + .35 * np.sin(2 * np.pi * f * 2.003 * t) for f in chord) * (3 / len(chord))
        env = np.minimum(1, t / .6) * np.minimum(1, (bar - t) / .4)
        _mix(track, (pad * env * .06).astype(np.float32), b * bar)
        for k in range(8):
            f = chord[k % len(chord)] * (2 if k % 4 < 2 else 4)
            _mix(track, _tone(.35, f, f, 9) * .05, b * bar + k * beat / 2)
        for q in range(4):
            if q % 2 == 0:
                _mix(track, _tone(.25, 110, 45, 16) * .35, b * bar + q * beat)
            hat = _noise(.05) * np.exp(-np.arange(round(.05 * RATE)) / RATE * 90)
            _mix(track, (hat - _lowpass(hat, 6000)) * .05, b * bar + q * beat + beat / 2)
    track = track[:round(seconds * RATE)]
    if speech:
        track *= duck_curve(seconds, speech)[:len(track)]
    fade = min(len(track), RATE * 2)
    track[-fade:] *= np.linspace(1, 0, fade)
    sf.write(path, np.clip(track, -.95, .95), RATE)


# Rhubarb-style mouth shapes: A closed (M/B/P), B teeth (most consonants, EE), C open, D wide, E rounded,
# F pucker (OO/W), G F/V, H L/TH, X rest. Kokoro emits misaki IPA with A/I/O/W/Y as diphthongs.
VISEME = {**{c: "A" for c in "pbm"}, **{c: "B" for c in "kgtdnszʃʒjhŋɹɾʧʤi"}, **{c: "C" for c in "ɛeʌəɪA"},
          **{c: "D" for c in "ɑæaIW"}, **{c: "E" for c in "ɔOYɜɚᵊ"}, **{c: "F" for c in "uwʊ"},
          **{c: "G" for c in "fv"}, **{c: "H" for c in "lθð"}}


def visemes(results, fps: int, lead: float = .05, min_hold: int = 2) -> list[list]:
    """[[frame, shape], ...] from Kokoro token phonemes, led ~1.5 frames ahead, each shape held >= min_hold frames."""
    cues, offset = [], 0.0
    for result in results:
        for token in result.tokens or []:
            if token.start_ts is None or not token.phonemes:
                continue
            units = [VISEME[c] for c in token.phonemes if c in VISEME]
            if not units:
                continue
            start, end = offset + token.start_ts - lead, offset + token.end_ts - lead
            step = (end - start) / len(units)
            for k, shape in enumerate(units):
                cues.append((max(0.0, start + k * step), shape))
            cues.append((end, "X"))
        offset += len(result.audio) / RATE
    frames: list[list] = []
    for t, shape in sorted(cues):
        frame = round(t * fps)
        if frames and frame - frames[-1][0] < min_hold:
            if frames[-1][1] == "X" or shape == "A":   # closures win so plosives read
                frames[-1][1] = shape
            continue
        if not frames or frames[-1][1] != shape:
            frames.append([frame, shape])
    return frames


def mouth_envelope(audio: np.ndarray, fps: int) -> list[float]:
    hop = RATE / fps
    frames = math.ceil(len(audio) / hop)
    rms = np.array([np.sqrt(np.mean(audio[round(i * hop):round((i + 1) * hop)] ** 2) or 0) for i in range(frames)])
    peak = np.percentile(rms, 95) or 1
    smooth = np.convolve(np.clip(rms / peak, 0, 1), [.25, .5, .25], mode="same")
    return [round(float(x), 2) for x in smooth]


def word_timings(results) -> list[dict]:
    """Kokoro token timestamps -> [{w, s, e}] with punctuation attached to the preceding word."""
    words, offset = [], 0.0
    for result in results:
        for token in result.tokens or []:
            if token.start_ts is None or token.end_ts is None:
                continue
            if words and not any(c.isalnum() for c in token.text):
                words[-1]["w"] += token.text
                continue
            words.append({"w": token.text, "s": round(offset + token.start_ts, 3), "e": round(offset + token.end_ts, 3)})
        offset += len(result.audio) / RATE
    return words
