"""V2.2 premium (FIELDNOTES) QA: mobile typography, frame-0 hook, character consistency, CTA truthfulness, pacing.

All checks are deterministic and read the render metadata (props.json) plus brand/*.json. Font sizes are mirrored from
src/premium/Objects.tsx (PREMIUM_TEXT); tests/test_v22.py fails if the TSX drops below these numbers.
Nothing here is a model judgment.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIN = {"hook": 80, "heading": 64, "body": 40, "caption": 48, "meta": 32, "code": 30}   # code: monospaced lines, sized to the longest line

# layout -> [(field, clip chars, font px, class)] — the clip limit is where the component truncates with an ellipsis.
PREMIUM_TEXT = {
    "hookBold": [("heading", 52, 104, "hook")], "hookStack": [("heading", 52, 104, "hook")],
    "repoCard": [("label", 16, 64, "heading")],
    "nodeGraph": [("points", 28, 44, "body")], "repoConnect": [("points", 28, 44, "body")], "flowDiagram": [("nodes", 30, 44, "body")],
    "steps": [("points", 44, 44, "body")], "timeline": [("timeline", 44, 44, "body")], "listStack": [("points", 44, 44, "body")],
    "codeBlock": [("heading", 26, 32, "meta"), ("code", 999, 30, "code")], "terminal": [("points", 30, 40, "body")],
    "splitCompare": [("compare", 60, 42, "body")], "compare": [("compare", 60, 42, "body")],
    "warningCard": [("heading", 40, 76, "heading"), ("points", 40, 44, "body")],
    "browserMock": [("heading", 28, 64, "heading"), ("points", 26, 42, "body")],
    "deviceMock": [("heading", 26, 40, "body")], "chat": [("heading", 26, 40, "body")],
    "chips": [("points", 22, 44, "body")], "outroCTA": [("cta_secondary", 34, 56, "caption")],
}
HEADLINE_PX = 60          # kinetic top headline (caption role) — brand/tokens.json type.headline
BIG_REACTIONS = {"surprised", "celebrating"}
DM_PROMISE = re.compile(r"\b(dm|direct message|i'?ll send|we'?ll send|send you|in your inbox)\b", re.I)


def _brand(name: str) -> dict:
    return json.loads((ROOT / "brand" / name).read_text())


def _texts(field: str, scene: dict) -> list[str]:
    vd = scene.get("visualData") or {}
    if field == "points":
        return scene.get("points") or []
    if field in ("heading", "label"):
        return [scene.get(field) or ""]
    if field in ("nodes", "timeline"):
        return vd.get(field) or vd.get("steps") or scene.get("points") or []
    if field == "compare":
        return (vd.get("compare_left") or []) + (vd.get("compare_right") or []) + (vd.get("prompt_after") or [])
    if field == "cta_secondary":
        return [(scene.get("cta") or {}).get("secondary", "")]
    return []


def checks(props: dict) -> list[dict]:
    rows: list[dict] = []

    def add(name, passed, detail, scene=None, kind="brand", **extra):
        rows.append({"check": name, "passed": bool(passed), "detail": detail, "scene": scene, "mandatory": False,
                     "basis": "deterministic", "kind": kind, **extra})

    tokens = _brand("tokens.json")
    fps = props["fps"]
    scenes = props["scenes"]
    beats = [(s, b) for s in scenes for b in s.get("beats", [])]
    # ---- mobile typography
    add("headline_size", tokens["type"]["headline"] >= MIN["caption"], f"kinetic headline {tokens['type']['headline']}px (caption min {MIN['caption']})",
        kind="tiny_text")
    add("meta_size", tokens["type"]["masthead"] >= MIN["meta"] and tokens["type"]["minMeta"] >= MIN["meta"],
        f"masthead {tokens['type']['masthead']}px, meta {tokens['type']['minMeta']}px (min {MIN['meta']})", kind="tiny_text")
    for s, b in beats:
        sid = s.get("id")
        for field, limit, px, cls in PREMIUM_TEXT.get(b.get("layout", ""), []):
            if px < MIN[cls]:
                add("font_size", False, f"{b['layout']}.{field} {px}px < {cls} minimum {MIN[cls]}px", sid, kind="tiny_text")
            for text in _texts(field, s):
                if len(text) > limit:
                    add("text_fits", False, f"{b['layout']}.{field} '{text[:40]}' is {len(text)} chars > {limit} (ellipsis)", sid,
                        kind="overflow", field=field, limit=limit, layout=b["layout"])
    # ---- frame-0 hook
    first = beats[0][1] if beats else {}
    add("hook_frame0", first.get("layout") in ("hookBold", "hookStack") and bool(scenes[0].get("heading")) and first.get("transition") == "cut",
        f"first beat {first.get('layout')} / {first.get('transition')}: '{scenes[0].get('heading', '')[:50]}'", scenes[0].get("id") if scenes else None)
    # ---- character consistency
    chars = [(s.get("id"), b.get("character") or {}) for s, b in beats]
    on = any(c.get("scale") not in (None, "hidden") for _, c in chars)
    if on:
        scales = set(_brand("character/identity.json")["scales"]) | {"hidden"}
        add("character_staged", all(c for _, c in chars), "every beat has a staging decision")
        add("character_scales", all(c.get("scale") in scales for _, c in chars), f"scales used {sorted({c.get('scale') for _, c in chars})}")
        add("signature_entrance", chars[0][1].get("scale") == "closeup", f"hook scale {chars[0][1].get('scale')}", chars[0][0])
        outro = [(sid, c) for (s, b), (sid, c) in zip(beats, chars) if b.get("layout") == "outroCTA"]
        add("signature_cta", bool(outro) and all(c.get("state") == "pointing" and c.get("wink") for _, c in outro),
            "points at the keyword and winks" if outro else "no outroCTA beat", outro[0][0] if outro else None)
        big = [sid for sid, c in chars if c.get("state") in BIG_REACTIONS]
        add("one_reveal_reaction", len(big) <= 1, f"{len(big)} big reaction(s): {big}")
        hidden = [sid for (s, b), (sid, c) in zip(beats, chars) if c.get("scale") == "hidden" and b.get("layout") not in ("cinematic", "motionClip")]
        add("character_present", not hidden, f"hidden outside footage in {hidden}" if hidden else "present on every non-footage beat")
    name = _brand("character/identity.json").get("provisional_name", "")
    rendered = json.dumps([{k: s.get(k) for k in ("heading", "points", "label", "caption", "emphasis", "visualData")} for s in scenes])
    add("no_unapproved_name", not name or (props.get("characterName") == name) or name.lower() not in rendered.lower(),
        f"provisional name '{name}' {'absent from' if name.lower() not in rendered.lower() else 'appears in'} on-screen text")
    # ---- CTA
    outro_scene = next((s for s in scenes if s.get("role") == "outro"), scenes[-1] if scenes else {})
    cta = outro_scene.get("cta") or {}
    kw = cta.get("keyword", "")
    add("cta_keyword", bool(kw) and kw.lower() in outro_scene.get("narration", "").lower(),
        f"keyword '{kw}' {'spoken' if kw and kw.lower() in outro_scene.get('narration', '').lower() else 'missing from narration'}", outro_scene.get("id"))
    dm_ok = _brand("cta_templates.json")["fulfillment"].get("dm_delivery_enabled", False)
    promise = bool(DM_PROMISE.search(outro_scene.get("narration", "") + " " + cta.get("secondary", "")))
    add("cta_truthful", dm_ok or not promise, "no DM promise without a delivery integration" if not promise else "narration promises a DM", outro_scene.get("id"))
    # ---- pacing
    rhythm = _brand("motion.json")["rhythm"]
    short = [f"{s.get('id')}:{b['layout']} {b['e'] - b['s']:.1f}s" for s, b in beats
             if b.get("layout") not in ("loop",) and b["e"] - b["s"] < rhythm["min_hold_seconds"] - .4 and b is not s["beats"][-1]]
    add("min_hold", not short, f"beats under {rhythm['min_hold_seconds'] - .4:.1f}s: {short}" if short else "all beats hold long enough", kind="pacing")
    starts = [(s["from"] / fps) + b["s"] for s, b in beats]
    busiest = max((sum(1 for t in starts if a <= t < a + 10) for a in starts), default=0)
    add("cuts_per_10s", busiest <= rhythm["max_cuts_per_10s"] + 1, f"busiest 10 s window has {busiest} cuts (target ≤ {rhythm['max_cuts_per_10s']})", kind="pacing")
    return rows
