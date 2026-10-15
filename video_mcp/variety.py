"""Seeded per-video look and per-beat layout planning, with a history that penalizes recent reuse.

Brand layer (fixed): typefaces, mascot, safe zones, SFX palette. Everything below is varied per video.
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

PALETTES = ["paper-red", "midnight-lime", "cream-cobalt", "ink-orange", "mint-forest", "lilac-ink", "blueprint", "sand-teal"]
BACKGROUNDS = ["grain", "dots", "grid", "mesh", "lines", "flat"]
TEMPERAMENTS = ["snappy", "smooth", "editorial"]
CAPTIONS = ["pill", "bold", "editorial"]
TRANSITIONS = ["whip", "zoom", "push", "mask", "cut"]
OUTFITS = ["#2f3b52", "#c2410c", "#0f766e", "#6d28d9", "#1f2937", "#be123c", "#2563eb"]
HAIR = ["#3b2a21", "#1c1917", "#7c4a2d", "#a16207"]
MUSIC = [{"progression": p, "bpm": b} for p in range(4) for b in (84, 92, 100)]

STRUCTURAL = {"repoCard", "docStamp", "hookStack", "recap"}
REPO_FOLLOW = ["terminal", "chips", "starMeter", "heroWord", "listStack", "deviceMock", "mascotCloseup", "quote"]
DOC_OPEN = ["docStamp", "heroWord", "bigNumber"]
DOC_FOLLOW = ["listStack", "nodeGraph", "quote", "deviceMock", "chat", "heroWord", "mascotCloseup", "steps", "compare"]
HOOK_OPEN = ["hookStack", "heroWord", "bigNumber"]
ANCHOR = {"heroWord": "right", "bigNumber": "left", "quote": "peek", "mascotCloseup": "center", "hookStack": "right",
          "repoCard": "right", "terminal": "left", "chips": "right", "starMeter": "left", "listStack": "right",
          "deviceMock": "left", "docStamp": "right", "nodeGraph": "left", "chat": "right", "steps": "left",
          "compare": "peek", "recap": "right", "loop": "right"}


def _pick(rng: random.Random, options: list, recent: list) -> object:
    weights = [0.12 if o in recent[-2:] else 0.45 if o in recent else 1.0 for o in options]
    return rng.choices(options, weights=weights)[0]


def choose_variant(seed: str, history_path: Path) -> dict:
    history = json.loads(history_path.read_text()) if history_path.exists() else []
    recent = lambda key: [h.get(key) for h in history[-4:]]
    rng = random.Random(seed)
    variant = {
        "seed": seed,
        "palette": _pick(rng, PALETTES, recent("palette")),
        "background": _pick(rng, BACKGROUNDS, recent("background")),
        "temperament": _pick(rng, TEMPERAMENTS, recent("temperament")),
        "captions": _pick(rng, CAPTIONS, recent("captions")),
        "transitions": rng.sample(TRANSITIONS, 3),
        "outfit": _pick(rng, OUTFITS, recent("outfit")),
        "hair": rng.choice(HAIR),
        "music": _pick(rng, MUSIC, recent("music")),
        "camera": rng.choice([0.8, 1.0, 1.2]),
    }
    return variant


def remember(variant: dict, layouts: list[str], history_path: Path):
    history = json.loads(history_path.read_text()) if history_path.exists() else []
    history.append({**{k: v for k, v in variant.items() if k != "seed"}, "layouts": layouts})
    history_path.write_text(json.dumps(history[-20:], indent=1))


def split_beats(words: list[dict], audio_seconds: float, min_len=1.3, max_len=3.0) -> list[dict]:
    """Cut a scene into beats at punctuation once a beat is long enough, or at any word once it is too long."""
    beats, start, first = [], 0.0, 0
    for i, word in enumerate(words):
        length = word["e"] - start
        boundary = re.search(r"[.,!?;:—]$", word["w"])
        if (boundary and length >= min_len) or length >= max_len:
            beats.append({"s": round(start, 3), "e": round(word["e"], 3), "w": [first, i]})
            start, first = word["e"], i + 1
    if first < len(words):
        if beats and audio_seconds - start < 1.0:
            beats[-1]["e"], beats[-1]["w"][1] = round(audio_seconds, 3), len(words) - 1
        else:
            beats.append({"s": round(start, 3), "e": round(audio_seconds, 3), "w": [first, len(words) - 1]})
    if not beats:
        beats = [{"s": 0.0, "e": round(audio_seconds, 3), "w": [0, max(0, len(words) - 1)]}]
    beats[0]["s"] = 0.0
    beats[-1]["e"] = round(audio_seconds, 3)   # the last beat holds through the breath after the line
    return beats


def _focus(scene: dict, text: str) -> str:
    """The word or phrase a beat is about: emphasis, a number, the item label, or the longest word."""
    lower = text.lower()
    if scene.get("emphasis") and scene["emphasis"].lower() in lower:
        return scene["emphasis"]
    number = re.search(r"\$?\d[\d,.]*\s?(?:%|million|billion|thousand|GB|TB|x)?", text)
    if number:
        return number.group(0).strip()
    if scene.get("label") and scene["label"].lower() in lower:
        return scene["label"]
    words = [w.strip(".,!?;:'\"()") for w in text.split()]
    return max(words, key=len) if words else scene.get("heading", "")


def plan_layouts(scenes: list[dict], variant: dict) -> list[str]:
    """Assign a layout, focus, transition and camera move to every beat. Mutates scenes; returns layout order."""
    rng = random.Random(variant["seed"] + ":layouts")
    used: dict[str, int] = {}
    order: list[str] = []
    for index, scene in enumerate(scenes):
        is_last = index == len(scenes) - 1
        for b, beat in enumerate(scene["beats"]):
            text = " ".join(w["w"] for w in scene["words"][beat["w"][0]:beat["w"][1] + 1])
            beat["text"] = text
            beat["focus"] = _focus(scene, text)
            has_number = bool(re.search(r"\d", text))
            if scene["visual"] == "hook" and b == 0:
                options = [o for o in HOOK_OPEN if o != "bigNumber" or has_number]
                options = ["hookStack"] if scene.get("_roundup") and rng.random() < .5 else options
            elif scene["visual"] == "repo" and b == 0:
                options = ["repoCard"]
            elif scene["visual"] == "doc" and b == 0:
                options = [o for o in DOC_OPEN if o != "bigNumber" or scene.get("stat")]
            elif is_last and b == len(scene["beats"]) - 1:
                options = ["loop"]
            elif scene["visual"] == "outro" and b == 0:
                options = ["recap"]
            elif scene["visual"] in ("hook", "outro") or not scene.get("points"):
                options = ["heroWord", "quote", "mascotCloseup"] + (["bigNumber"] if has_number else [])
            elif scene["visual"] == "repo":
                options = REPO_FOLLOW + (["bigNumber"] if has_number else [])
            else:
                options = DOC_FOLLOW + (["bigNumber"] if has_number else [])
            fresh = [o for o in options if (not order or o != order[-1]) and (o in STRUCTURAL or o == "loop" or used.get(o, 0) < 2)]
            pool = fresh or options
            least = min(used.get(o, 0) for o in pool)
            layout = rng.choice([o for o in pool if used.get(o, 0) == least])
            used[layout] = used.get(layout, 0) + 1
            order.append(layout)
            beat["layout"] = layout
            beat["anchor"] = ANCHOR.get(layout, "right")
            beat["transition"] = "cut" if not order[:-1] else rng.choice(variant["transitions"])
            beat["punch"] = bool(scene.get("emphasis")) and scene["emphasis"].lower() in text.lower()
    return order
