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
          "compare": "peek", "recap": "right", "loop": "right", "codeBlock": "left", "flowDiagram": "peek", "timeline": "right",
          "chartBars": "left", "browserMock": "left", "warningCard": "right", "splitCompare": "peek", "cinematic": "peek"}
# Premium editorial themes (V2). A video keeps one theme for every scene.
THEMES = ["carbon", "midnight", "warm-editorial", "minimal-white", "tech-mono", "soft-gradient", "product-launch", "cinematic-dark"]


def _pick(rng: random.Random, options: list, recent: list) -> object:
    weights = [0.12 if o in recent[-2:] else 0.45 if o in recent else 1.0 for o in options]
    return rng.choices(options, weights=weights)[0]


def choose_variant(seed: str, history_path: Path, theme: str | None = None, character: bool = True) -> dict:
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
    if theme:
        # A storyboard theme replaces the seeded fun palette; motion stays restrained for editorial work.
        variant.update(theme=theme if theme in THEMES else _pick(rng, THEMES, recent("theme")), palette="",
                       background="flat" if variant["background"] in ("dots", "lines") else variant["background"],
                       camera=min(variant["camera"], 1.0))
    variant["character"] = character
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


FUNCTION_WORDS = set("the and but for with from that this these those your their there here into onto about after before "
                     "because while where which would could should doesn't isn't aren't don't won't can't just also very "
                     "only then than what when will have has had been being".split())


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
    # Prefer a content word: no contractions or function words as the hero of a beat.
    content = [w for w in words if "'" not in w and "’" not in w and w.lower() not in FUNCTION_WORDS and len(w) > 2]
    return max(content or words, key=len) if words else scene.get("heading", "")


PACE = {"emphasis": (1.0, 2.4), "medium": (1.3, 3.0), "demonstration": (2.4, 5.5), "pause": (1.6, 3.6), "montage": (.9, 1.8)}


def plan_layouts(scenes: list[dict], variant: dict) -> list[str]:
    """Assign a layout, focus, transition and camera move to every beat. Mutates scenes; returns layout order.

    Layouts are chosen semantically (creative/semantic_router.py): what the narration means outranks variety.
    Structural V1 rules still hold: repo items open on their repo card, the outro opens on the recap, the final beat
    loops back to the opening frame, and no layout plays twice in a row."""
    from .creative import semantic_router as sr
    rng = random.Random(variant["seed"] + ":layouts")
    theme = variant.get("theme", "")
    character = variant.get("character", True)
    used: dict[str, int] = {}
    order: list[str] = []
    beat_no = 0
    list_items = sum(1 for s in scenes if s.get("item", 0) > 0)
    for index, scene in enumerate(scenes):
        scene["_listItems"] = list_items
        is_last = index == len(scenes) - 1
        scene["_repo"] = bool(scene.get("_roundup")) and scene.get("item", 0) > 0
        b = 0
        while b < len(scene["beats"]):
            beat = scene["beats"][b]
            text = " ".join(w["w"] for w in scene["words"][beat["w"][0]:beat["w"][1] + 1])
            beat["text"] = text
            beat["focus"] = _focus(scene, text)
            if is_last and b == len(scene["beats"]) - 1 and len(scenes) > 1:
                layout, reason = "loop", {"rule": "final beat loops to the opening frame"}
            else:
                ctx = sr.beat_context(scene, beat, b, character=character and scene.get("character", True) is not False)
                allowed = None
                if b == 0 and scene["visual"] == "repo" and scene["_repo"]:
                    allowed = ["repoCard"]
                elif b == 0 and scene["visual"] == "outro" and list_items >= 2:
                    allowed = ["recap"]
                elif b == 0 and scene["visual"] == "hook":
                    allowed = HOOK_OPEN + ["cinematic"]
                    if scene.get("_roundup") and not scene.get("media"):
                        allowed = ["hookStack", "heroWord", "bigNumber"]
                    if list_items < 2:
                        allowed = [x for x in allowed if x != "hookStack"]
                elif b == 0 and scene["visual"] == "doc" and ctx["intent"] in ("generic", "list"):
                    allowed = DOC_OPEN
                avoid = set(scene.get("avoidLayouts") or [])
                if avoid:
                    allowed = [x for x in (allowed or list(sr.CATALOG)) if x not in avoid] or None
                layout, reason = sr.choose(ctx, order, used, variant["seed"], beat_no, theme, allowed)
            used[layout] = used.get(layout, 0) + 1
            previous = order[-1] if order else None
            order.append(layout)
            beat_no += 1
            beat["layout"] = layout
            beat["layoutReason"] = reason
            beat["anchor"] = ANCHOR.get(layout, "right")
            if previous is None:
                beat["transition"] = "cut"
            elif layout == "cinematic" or previous == "cinematic":
                beat["transition"] = "mask" if "mask" in variant["transitions"] else variant["transitions"][0]
            else:
                beat["transition"] = rng.choice(variant["transitions"])
            beat["punch"] = bool(scene.get("emphasis")) and scene["emphasis"].lower() in text.lower()
            if b == 0 and layout != "loop" and len(scene["beats"]) > 1 and sr.holds_scene(layout, scene.get("pace", "medium")):
                # Hold the explanatory visual for the whole line; keep a separate final beat only for the loop-back.
                keep = scene["beats"][-1] if is_last and len(scenes) > 1 else None
                rest = scene["beats"][1:-1] if keep else scene["beats"][1:]
                if rest:
                    beat["e"], beat["w"] = rest[-1]["e"], [beat["w"][0], rest[-1]["w"][1]]
                    beat["text"] = " ".join(w["w"] for w in scene["words"][beat["w"][0]:beat["w"][1] + 1])
                    beat["punch"] = bool(scene.get("emphasis")) and scene["emphasis"].lower() in beat["text"].lower()
                    beat["held"] = True
                scene["beats"] = [beat] + ([keep] if keep else [])
            b += 1
    return order
