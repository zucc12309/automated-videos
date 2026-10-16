"""Semantic scene orchestration: choose each beat's layout from what the narration means.

Score = 4.0 * semantic relevance          (intent -> layout table; dominates)
      + 0.8 * narrative fit               (role / position in the story)
      + 1.0 * readability                 (beat long enough for the layout's text density)
      - 1.5 * recent usage                (same layout in the last beats / overused)
      - 0.6 * motion discontinuity        (same motion family back-to-back is fine once, not thrice)
      - 0.4 * cost                        (cinematic footage costs money and time)
      - 0.3 * complexity on short beats
      + 0.2 * brand consistency           (layout family suits the theme)
Hard requirements (asset/data availability) exclude a layout instead of lowering its score.
Ties break deterministically on sha256(seed, beat index, layout), so the same storyboard + seed gives the same plan.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

# ---------- intent inference ----------

_PATTERNS: list[tuple[str, str]] = [
    ("warning", r"\b(warn|risk|careful|danger|caveat|limitation|don't|do not|never|beware|security hole|leak|breaks?)\b"),
    ("comparison", r"\b(vs\.?|versus|compared (to|with)|instead of|unlike|better than|faster than|before and after|rather than)\b"),
    ("code", r"\b(npm|pip|npx|brew|git clone|command|cli|terminal|shell script|function|source code|code|install|import|config file|yaml|json)\b"),
    ("api_flow", r"\b(api|endpoint|request|response|webhook|sdk|calls?|returns?|sends?|tool calls?)\b"),
    ("architecture", r"\b(architecture|layer|pipeline|server|client|protocol|orchestrat\w*|agents? (talk|connect)|connects?|integrat\w*)\b"),
    ("timeline", r"\b(in 20\d\d|since 20\d\d|by 20\d\d|timeline|roadmap|years? ago|history of)\b"),
    ("growth", r"\b(grew|growth|grows|doubled|tripled|increase[sd]?|up \d|from \d.* to \d|faster|scale[sd]?)\b"),
    ("statistic", r"(\$?\d[\d,.]*\s?(%|percent|x\b|times|million|billion|thousand|k\b|users|stars|hours|minutes))"),
    ("process", r"\b(step|steps|first|next|finally|then|workflow|process|how to|set ?up)\b"),
    ("app_demo", r"\b(app|dashboard|interface|ui|browser|extension|editor|ide|phone|mobile|click|screen)\b"),
    ("product_intro", r"\b(meet|introduc\w*|launch\w*|new tool|announc\w*|unveil\w*|just shipped|ships?)\b"),
    ("real_world", r"\b(world|city|office|factory|people|teams?|desk|studio|room|future|imagine)\b"),
    ("quote", r"[\"“].{12,}[\"”]|\b(said|says|according to)\b"),
    ("list", r"\b(three|four|five|several|tools|features|options|ways|things)\b"),
]


def infer_intent(text: str, *, role: str = "body", visual: dict | None = None, has_repo: bool = False, given: str = "generic") -> str:
    if given and given != "generic":
        return given
    if role == "hook":
        return "hook"
    if role == "outro":
        return "recap"
    visual = visual or {}
    if visual.get("code"):
        return "code"
    if visual.get("compare_left") and visual.get("compare_right"):
        return "comparison"
    if visual.get("series_values"):
        return "growth"
    if visual.get("timeline"):
        return "timeline"
    if visual.get("nodes"):
        return "architecture"
    if has_repo:
        return "repository"
    lower = text.lower()
    for intent, pattern in _PATTERNS:
        if re.search(pattern, lower):
            return intent
    return "generic"


# ---------- layout catalogue ----------

@dataclass(frozen=True)
class LayoutSpec:
    name: str
    family: str                  # motion family for continuity: type | card | diagram | device | data | footage | character
    min_seconds: float           # time needed to read it
    complexity: float            # 0 simple .. 1 dense
    needs: tuple[str, ...] = ()  # hard requirements
    cost: float = 0.0
    themes: tuple[str, ...] = ()  # themes it particularly suits (brand consistency bonus)


CATALOG: dict[str, LayoutSpec] = {s.name: s for s in [
    LayoutSpec("heroWord", "type", 1.0, .1),
    LayoutSpec("bigNumber", "data", 1.4, .2, ("number",)),
    LayoutSpec("quote", "type", 1.8, .3),
    LayoutSpec("mascotCloseup", "character", 1.2, .1, ("character",)),
    LayoutSpec("listStack", "card", 2.0, .5, ("points2",)),
    LayoutSpec("steps", "diagram", 2.2, .6, ("points2",)),
    LayoutSpec("compare", "card", 2.2, .6, ("points2",)),
    LayoutSpec("repoCard", "card", 2.0, .6, ("repo",)),
    LayoutSpec("terminal", "device", 2.0, .5, ("repo_or_points",), themes=("tech-mono", "carbon", "midnight")),
    LayoutSpec("chips", "card", 1.5, .4, ("points2",)),
    LayoutSpec("starMeter", "data", 1.6, .3, ("repo",)),
    LayoutSpec("deviceMock", "device", 2.0, .5, ("points1",)),
    LayoutSpec("chat", "device", 2.0, .5, ("points1",)),
    LayoutSpec("nodeGraph", "diagram", 2.4, .7, ("nodes_or_points",)),
    LayoutSpec("hookStack", "type", 1.2, .3, ("hook", "items")),
    LayoutSpec("docStamp", "card", 1.6, .4, ("item",)),
    LayoutSpec("recap", "card", 2.0, .5, ("outro", "items")),
    # V2 semantic layouts
    LayoutSpec("codeBlock", "device", 2.6, .8, ("code",), themes=("tech-mono", "carbon", "midnight")),
    LayoutSpec("flowDiagram", "diagram", 2.6, .7, ("nodes_or_points",)),
    LayoutSpec("timeline", "diagram", 2.4, .6, ("timeline",)),
    LayoutSpec("chartBars", "data", 2.2, .6, ("series",)),
    LayoutSpec("browserMock", "device", 2.2, .5, ("points1",), themes=("minimal-white", "product-launch", "soft-gradient")),
    LayoutSpec("warningCard", "card", 1.8, .4, ()),
    LayoutSpec("splitCompare", "card", 2.4, .7, ("compare",)),
    LayoutSpec("cinematic", "footage", 1.5, .2, ("footage",), cost=1.0, themes=("cinematic-dark", "midnight", "carbon")),
    # V2.1 retention layouts
    LayoutSpec("hookBold", "type", .8, .3, ("hook",)),
    LayoutSpec("readmeScroll", "device", 2.4, .6, ("repo",)),
    LayoutSpec("repoConnect", "diagram", 2.2, .5, ("repo_or_points",)),
    LayoutSpec("outroCTA", "card", 2.0, .4, ("outro",)),
    LayoutSpec("motionClip", "footage", 1.0, .1, ("motion_clip",)),
]}

RELEVANCE: dict[str, dict[str, float]] = {
    "hook": {"hookBold": 1.0, "hookStack": .85, "heroWord": .8, "bigNumber": .75, "cinematic": .7, "quote": .45},
    "product_intro": {"browserMock": .9, "heroWord": .85, "deviceMock": .75, "chips": .6, "cinematic": .6},
    "api_flow": {"flowDiagram": 1.0, "codeBlock": .75, "nodeGraph": .65, "terminal": .55, "chat": .4},
    "repository": {"repoCard": 1.0, "readmeScroll": .8, "repoConnect": .78, "terminal": .65, "starMeter": .6, "chips": .5, "codeBlock": .5},
    "comparison": {"splitCompare": 1.0, "compare": .9, "chartBars": .5},
    "process": {"steps": 1.0, "timeline": .7, "flowDiagram": .65, "listStack": .55},
    "architecture": {"nodeGraph": 1.0, "flowDiagram": .85, "steps": .4},
    "code": {"codeBlock": 1.0, "terminal": .9},
    "growth": {"chartBars": 1.0, "bigNumber": .8, "starMeter": .55},
    "statistic": {"bigNumber": 1.0, "chartBars": .6, "starMeter": .4},
    "app_demo": {"deviceMock": 1.0, "browserMock": .95, "chat": .6},
    "real_world": {"cinematic": 1.0, "heroWord": .55, "quote": .5},
    "timeline": {"timeline": 1.0, "steps": .7},
    "warning": {"warningCard": 1.0, "quote": .45, "docStamp": .4},
    "quote": {"quote": 1.0, "heroWord": .6},
    "list": {"listStack": 1.0, "chips": .8, "steps": .55},
    "recap": {"outroCTA": 1.0, "recap": .9, "listStack": .5, "heroWord": .4},
    "generic": {"heroWord": .6, "quote": .55, "listStack": .55, "chips": .5, "docStamp": .45, "mascotCloseup": .4,
                "nodeGraph": .3, "chat": .3, "deviceMock": .3},
}
SUPPORT = {"heroWord": .35, "quote": .3, "chips": .25, "listStack": .25}   # weak default relevance for supporting beats


def _requirements_met(spec: LayoutSpec, ctx: dict) -> bool:
    checks = {
        "number": ctx["has_number"], "character": ctx["character"], "points1": ctx["points"] >= 1, "points2": ctx["points"] >= 2,
        "repo": ctx["has_repo"], "repo_or_points": ctx["has_repo"] or ctx["points"] >= 2, "hook": ctx["role"] == "hook",
        "item": ctx["item"] > 0, "outro": ctx["role"] == "outro", "code": ctx["code"], "nodes_or_points": ctx["nodes"] or ctx["points"] >= 2,
        "timeline": ctx["timeline"], "series": ctx["series"], "compare": ctx["compare"], "footage": ctx["footage"],
        "items": ctx.get("list_items", 0) >= 2, "motion_clip": ctx.get("motion_clip", False),
    }
    return all(checks[n] for n in spec.needs)


def _tiebreak(seed: str, beat_index: int, layout: str) -> str:
    return hashlib.sha256(f"{seed}|{beat_index}|{layout}".encode()).hexdigest()


def score(layout: str, ctx: dict, history: list[str], used: dict[str, int], theme: str) -> tuple[float, dict]:
    spec = CATALOG[layout]
    # Layouts unrelated to the intent fall back to their generic suitability, so an irrelevant layout never wins a tie.
    relevance = RELEVANCE.get(ctx["intent"], {}).get(layout) or RELEVANCE["generic"].get(layout, 0.0) * .6
    if not ctx["primary"]:
        relevance = max(relevance * .7, SUPPORT.get(layout, 0.0) + RELEVANCE["generic"].get(layout, 0) * .3)
    if ctx["preferred"] == layout:
        relevance = min(1.2, relevance + .5)
    narrative = 1.0 if (ctx["role"] == "hook" and spec.family == "type") or (ctx["role"] == "outro" and layout in ("recap", "outroCTA")) else .5
    readability = min(1.0, ctx["seconds"] / max(.1, spec.min_seconds))
    recent = (1.0 if history and history[-1] == layout else 0) + (.5 if layout in history[-4:] else 0) + .4 * max(0, used.get(layout, 0) - 1)
    families = [CATALOG[h].family for h in history[-2:] if h in CATALOG]
    discontinuity = 1.0 if len(families) == 2 and all(f == spec.family for f in families) else 0.0
    complexity = spec.complexity if ctx["seconds"] < 2.0 else 0.0
    brand = 1.0 if theme in spec.themes else 0.0
    parts = {"relevance": round(relevance, 3), "narrative": narrative, "readability": round(readability, 3), "recent": recent,
             "discontinuity": discontinuity, "cost": spec.cost, "complexity": complexity, "brand": brand}
    total = 4.0 * relevance + .8 * narrative + 1.0 * readability - 1.5 * recent - .6 * discontinuity - .4 * spec.cost - .3 * complexity + .2 * brand
    return round(total, 4), parts


OPENERS = {"repoCard", "docStamp", "hookStack", "hookBold", "recap", "outroCTA"}   # scene openers, never supporting beats


def choose(ctx: dict, history: list[str], used: dict[str, int], seed: str, beat_index: int, theme: str,
           allowed: list[str] | None = None, cap: int = 2) -> tuple[str, dict]:
    candidates = [name for name in (allowed or CATALOG) if name in CATALOG and _requirements_met(CATALOG[name], ctx)
                  and (ctx["primary"] or name not in OPENERS)]
    structural = {"repoCard", "docStamp", "hookStack", "recap", "cinematic"}
    # The usage cap keeps supporting beats varied; a scene's primary visual is chosen on meaning (recency still penalised).
    fresh = [c for c in candidates if (not history or c != history[-1]) and (c in structural or ctx["primary"] or used.get(c, 0) < cap)]
    pool = fresh or candidates or ["heroWord"]
    scored = sorted(((*score(c, ctx, history, used, theme), c) for c in pool),
                    key=lambda x: (-x[0], _tiebreak(seed, beat_index, x[2])))
    best_score, parts, best = scored[0]
    return best, {"score": best_score, "parts": parts, "intent": ctx["intent"],
                  "runner_up": scored[1][2] if len(scored) > 1 else None}


STRONG_BEAT_INTENTS = {"statistic", "comparison", "warning", "timeline"}


def beat_context(scene: dict, beat: dict, beat_no: int, *, character: bool) -> dict:
    text = beat.get("text", "")
    visual = scene.get("visualData") or {}
    role = scene.get("role") or ("hook" if scene.get("visual") == "hook" else "outro" if scene.get("visual") == "outro" else
                                 "item" if scene.get("item") else "body")
    primary = beat_no == 0
    scene_intent = infer_intent(scene.get("narration", ""), role=role, visual=visual, has_repo=bool(scene.get("_repo")),
                                given=scene.get("intent", "generic"))
    intent = scene_intent if primary else infer_intent(text, role="body", visual={}, given="generic")
    if not primary and intent not in STRONG_BEAT_INTENTS and scene_intent not in ("hook", "recap", "generic"):
        intent = scene_intent        # weak keyword hits on a supporting phrase do not override what the scene is about
    if not primary and role == "outro":
        intent = "generic"      # the payoff line stays a recap, not a new diagram
    if not primary and intent == "generic":
        intent = scene_intent if scene_intent not in ("hook", "recap") else "generic"     # repo items keep moving repo visuals
    return {"intent": intent, "primary": primary, "role": role, "item": scene.get("item", 0), "seconds": beat["e"] - beat["s"],
            "has_number": bool(re.search(r"\d", text)) or (primary and bool(scene.get("stat"))), "points": len(scene.get("points") or []),
            "has_repo": bool(scene.get("_repo")), "character": character, "code": bool(visual.get("code")),
            "nodes": len(visual.get("nodes") or []) >= 3, "timeline": len(visual.get("timeline") or visual.get("steps") or []) >= 2,
            "series": len(visual.get("series_values") or []) >= 2,
            "compare": bool(visual.get("compare_left")) and bool(visual.get("compare_right")),
            "footage": primary and bool(scene.get("media")), "preferred": scene.get("layoutHint", "") if primary else "",
            "list_items": scene.get("_listItems", 0), "motion_clip": primary and bool(scene.get("motionClip"))}


def _register_generated():
    """Approved generated components (component_forge.promote) join the catalogue with the intents they declared."""
    try:
        from .component_forge import approved_specs
        specs = approved_specs()
    except Exception:
        return
    valid = {"number", "points1", "points2", "code", "nodes_or_points", "timeline", "series", "compare", "items"}
    for spec in specs:
        CATALOG[spec["layout"]] = LayoutSpec(spec["layout"], "card", 2.0, .5, tuple(n for n in spec.get("needs", []) if n in valid))
        for intent in spec.get("intents", []):
            if intent in RELEVANCE:
                RELEVANCE[intent][spec["layout"]] = .85


_register_generated()


HOLD_FAMILIES = {"diagram", "device", "data", "footage"}


def holds_scene(layout: str, pace: str) -> bool:
    """Complex visuals stay on screen for the whole line instead of being cut into filler beats."""
    spec = CATALOG.get(layout)
    if not spec:
        return False
    if layout in ("outroCTA", "motionClip"):
        return True             # the ending and imported clips play through
    if layout in ("repoCard", "docStamp", "hookStack", "hookBold", "recap"):
        return False            # structural openers hand over to supporting beats (V1 rhythm)
    return spec.family in HOLD_FAMILIES or layout == "splitCompare" or (pace == "demonstration" and spec.complexity >= .5)
