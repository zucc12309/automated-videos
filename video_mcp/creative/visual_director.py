"""Visual director: plans the whole reel as one composition after layouts are chosen.

For every beat it decides the transition (by continuity with the previous beat), enforces rhythm (minimum hold,
maximum cuts per 10 s), and stages the character (state, scale, anchor, pointing, dimming) — recording why.
Signature behaviours (brand/character/identity.json): pop-up entrance on the hook, one 'reveal' reaction per video,
pointing + wink at the CTA.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DENSE = {"codeBlock", "terminal", "flowDiagram", "nodeGraph", "repoConnect", "readmeScroll", "splitCompare", "compare", "browserMock", "steps",
         "timeline", "listStack", "chips"}
DETAIL_OF_CARD = {"readmeScroll", "terminal", "repoConnect", "codeBlock", "chips", "listStack", "steps"}
FOOTAGE = {"cinematic", "motionClip"}
TYPING = {"codeBlock", "terminal"}
EXPLAIN = {"flowDiagram", "nodeGraph", "repoConnect"}
BIG = {"surprised", "celebrating"}


def _motion() -> dict:
    return json.loads((ROOT / "brand" / "motion.json").read_text())


def _merge_short(scene: dict, min_hold: float) -> list[str]:
    """Merge supporting beats shorter than min_hold into the previous beat (never the opener or the loop tail)."""
    notes, beats = [], scene["beats"]
    i = 1
    while i < len(beats):
        b = beats[i]
        if b.get("layout") != "loop" and b["e"] - b["s"] < min_hold:
            prev = beats[i - 1]
            prev["e"], prev["w"] = b["e"], [prev["w"][0], b["w"][1]]
            prev["text"] = (prev.get("text", "") + " " + b.get("text", "")).strip()
            notes.append(f"{scene.get('id')}: merged a {b['e'] - b['s']:.1f}s '{b.get('layout')}' beat into the previous one (min hold {min_hold}s)")
            beats.pop(i)
            continue
        i += 1
    return notes


def direct(scenes: list[dict], *, character_mode: str = "on") -> dict:
    rules = _motion()["rhythm"]
    notes: list[str] = []
    for s in scenes:
        notes += _merge_short(s, rules["min_hold_seconds"])
    flat = [(si, bi, b) for si, s in enumerate(scenes) for bi, b in enumerate(s["beats"])]
    # Rhythm: cap cuts per 10 s window by merging the shortest supporting beat of an over-busy window.
    t0 = 0.0
    for si, s in enumerate(scenes):
        s["_t0"] = t0
        t0 += s["frames"] / 30
    starts = [scenes[si]["_t0"] + b["s"] for si, bi, b in flat]
    for i in range(len(starts)):
        window = [j for j in range(len(starts)) if starts[i] <= starts[j] < starts[i] + 10]
        if len(window) > rules["max_cuts_per_10s"]:
            notes.append(f"window at {starts[i]:.1f}s has {len(window)} cuts (> {rules['max_cuts_per_10s']}); kept: each is a scene/structural change")
            break
    # One big reaction per video: a storyboard-requested surprise/celebration replaces the automatic reveal.
    reacted = any(s.get("character_action") in BIG for s in scenes)
    impressive = _impressive_scene(scenes)
    prev_layout, prev_si = None, None
    for si, s in enumerate(scenes):
        role = s.get("role", "body")
        for bi, b in enumerate(s["beats"]):
            layout = b["layout"]
            # ---- transition by continuity
            if prev_layout is None:
                tr, why = "cut", "first frame: the hook must be readable immediately"
            elif layout == "loop":
                tr, why = "cut", "loop tail cuts back to the opening frame so the CTA never overlaps the hook and the replay is seamless"
            elif si == prev_si and prev_layout == "repoCard" and layout in DETAIL_OF_CARD:
                tr, why = "expand", "the repo card expands into its own demonstration (same object continues)"
            elif si == prev_si and layout in DETAIL_OF_CARD | {"bigNumber", "heroWord"}:
                tr, why = "focus", "camera focuses into a detail of the same idea"
            elif si != prev_si and s.get("item") and scenes[prev_si].get("item"):
                tr, why = "push", "next numbered item slides in: list progression"
            elif layout in FOOTAGE or prev_layout in FOOTAGE:
                tr, why = "blurDissolve", "footage blends with graphics through a soft dissolve"
            else:
                tr, why = "blurDissolve", "unrelated objects: editorial blur dissolve"
            b["transition"] = tr
            # ---- character staging
            st = _stage(s, b, si, bi, role, layout, character_mode)
            if si == impressive and bi == 0 and not reacted and st["state"] not in ("pointing",):
                st.update(state="surprised", reason="signature reveal reaction (once per video) on the most impressive item")
                reacted = True
            if s.get("character_action") and bi == 0 and layout != "outroCTA":
                st.update(state=s["character_action"], reason=f"storyboard asked for '{s['character_action']}'")
            b["character"] = {k: v for k, v in st.items() if k != "reason"}
            b["direction"] = {"transition": why, "character": st["reason"], "layout": (b.get("layoutReason") or {}).get("intent")}
            prev_layout, prev_si = layout, si
    for s in scenes:
        s.pop("_t0", None)
    return {"notes": notes, "reveal_scene": scenes[impressive].get("id") if impressive is not None else None}


def _impressive_scene(scenes: list[dict]) -> int | None:
    """Most impressive item: highest star count for repos, else the first scene with a stat, else the 'after' of a fix."""
    best, idx = -1, None
    for i, s in enumerate(scenes):
        stars = s.get("_stars") or 0
        if stars > best and s.get("item"):
            best, idx = stars, i
    if idx is not None and best > 0:
        return idx
    for i, s in enumerate(scenes):
        if s.get("stat") or (s.get("visualData") or {}).get("prompt_after"):
            return i
    return None


def _stage(s: dict, b: dict, si: int, bi: int, role: str, layout: str, mode: str) -> dict:
    if mode == "off":
        return {"state": "idle", "scale": "hidden", "anchor": "home", "reason": "character disabled"}
    if si == 0 and bi == 0:
        return {"state": "speaking", "scale": "closeup", "anchor": "centre", "reason": "signature entrance: pops up under the hook and acknowledges the viewer"}
    if layout == "outroCTA":
        return {"state": "pointing", "scale": "medium", "anchor": "right", "point": "left", "wink": True,
                "reason": "signature CTA: points at the keyword and winks"}
    if layout in FOOTAGE:
        return {"state": "idle", "scale": "hidden", "anchor": "home", "reason": "footage needs the full frame"}
    if layout == "loop":
        return {"state": "speaking", "scale": "closeup", "anchor": "centre", "reason": "loop returns to the opening composition"}
    if layout == "repoCard":
        return {"state": "presenting", "scale": "medium", "anchor": "home", "point": "right", "reason": "introduces the repository it is next to"}
    if layout in TYPING:
        return {"state": "typing", "scale": "companion", "anchor": "home", "dim": .15, "reason": "small companion typing while code/commands run"}
    if layout in EXPLAIN:
        return {"state": "explaining", "scale": "companion", "anchor": "home", "point": "right", "dim": .1, "reason": "gestures toward the connection being drawn"}
    if layout == "warningCard" or s.get("intent") == "warning":
        return {"state": "warning", "scale": "medium", "anchor": "home", "reason": "reacts to the mistake/caution"}
    if layout in ("splitCompare", "compare"):
        return {"state": "thinking", "scale": "companion", "anchor": "home", "dim": .1, "reason": "considers before vs after without covering it"}
    if layout in DENSE:
        return {"state": "speaking", "scale": "companion", "anchor": "home", "dim": .15, "reason": "dense demonstration: small companion"}
    return {"state": "speaking", "scale": "medium", "anchor": "home", "reason": "explanation beat: medium presenter"}
