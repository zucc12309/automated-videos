"""Creative direction: produce a validated Storyboard from a topic, choosing providers per production mode with fallbacks.

LOCAL   script: Ollama -> template          direction: local heuristic director
CLAUDE  script + direction: Claude          fallback: Ollama -> template + local director
HYBRID  as CLAUDE, and cinematic scenes may be requested (generation happens later, behind the cost gate)
"""
from __future__ import annotations

import hashlib
import time

from ..providers.base import ProviderError
from ..providers.script_providers import OllamaProvider, TemplateProvider
from ..schemas.storyboard import THEMES, Storyboard, from_plan
from . import research, semantic_router

DEMONSTRATION = {"code", "architecture", "api_flow", "process", "timeline", "comparison"}


HOOK_SHOT = ("Slow push-in across a dark developer desk at night, monitor glow and shallow depth of field, premium technology "
             "commercial lighting, calm and precise, large empty area in the upper half for bold titles, no readable text, no logos")


def local_direction(board: Storyboard, settings, seed: str, cinematic: bool = False) -> Storyboard:
    """Heuristic director for LOCAL mode and for plans supplied without direction: intents, pacing, theme, character,
    and structured visual data derived only from text already in the plan / topic."""
    theme = settings.production.theme
    if theme not in THEMES:
        theme = THEMES[int(hashlib.sha256(seed.encode()).hexdigest(), 16) % len(THEMES)]
    board.creative_direction.theme = theme
    board.creative_direction.character = settings.production.character
    repos = {i + 1: r for i, r in enumerate(board.repos)}
    for scene in board.scenes:
        scene.intent = semantic_router.infer_intent(scene.narration, role=scene.role, visual=scene.visual.model_dump(),
                                                     has_repo=board.format == "roundup" and scene.item > 0, given=scene.intent)
        scene.pace = "emphasis" if scene.role == "hook" or scene.intent == "statistic" else \
            "demonstration" if scene.intent in DEMONSTRATION else "medium"
        if scene.intent in ("process", "timeline") and not scene.visual.steps:
            scene.visual.steps = scene.points[:4]
        if scene.intent in ("architecture", "api_flow") and not scene.visual.nodes and len(scene.points) >= 2:
            scene.visual.nodes = scene.points[:4]
        if scene.intent == "repository" and scene.item in repos and not scene.visual.code:
            scene.visual.code = [f"$ gh repo clone {repos[scene.item].get('full_name', '')}"[:48]]
        if scene.character is None:
            mode = settings.production.character
            scene.character = mode == "on" or (mode == "auto" and scene.role in ("hook", "outro"))
        scene.motion.camera = "static" if scene.pace == "demonstration" else "subtle_push"
        scene.motion.entrance = "mask" if scene.role == "hook" else "reveal"
        scene.motion.emphasis = "counter" if scene.stat else "highlight"
    hook = board.scenes[0]
    if cinematic and hook.role == "hook" and hook.cinematic is None:
        # HYBRID: one atmospheric establishing shot behind the bold hook; text stays Remotion typography.
        from ..schemas.storyboard import CinematicSpec
        hook.cinematic = CinematicSpec(prompt=HOOK_SHOT, duration_seconds=4, fallback_layout="hookBold")
        hook.render_engine = "cinematic"
    return board


def _script_provider(settings, decisions: list[dict]):
    ollama = OllamaProvider(settings)
    ok, why = ollama.available()
    if ok:
        return ollama
    decisions.append({"stage": "script", "provider": "ollama", "used": False, "reason": why, "fallback": "template"})
    return TemplateProvider(settings)


def script_locally(topic: dict, settings, decisions: list[dict]):
    count = len(topic["repos"]) if topic.get("kind") == "roundup" else int(getattr(settings, "story_points", None) or
                                                                            settings.model_extra.get("story_points", 4))
    provider = _script_provider(settings, decisions)
    try:
        result = provider.write_plan(topic, count)
    except ProviderError as exc:
        if provider.name == "template":
            raise
        decisions.append({"stage": "script", "provider": provider.name, "used": False, "reason": exc.message, "fallback": "template"})
        result = TemplateProvider(settings).write_plan(topic, count)
    decisions.append({"stage": "script", "provider": result.provider, "model": result.model, "used": True, "notes": result.notes})
    return result


def create_storyboard(topic: dict, settings, *, mode: str, video_id: str, seed: str, claude=None, gate=None,
                      decisions: list[dict] | None = None, cinematic: bool = False) -> tuple[Storyboard, dict, list]:
    """Returns (storyboard, verification report, usages). `claude` is a ClaudeProvider; `gate` the budget gate factory."""
    decisions = decisions if decisions is not None else []
    research_packet, sources = research.build_research(topic)
    fmt = "roundup" if topic.get("kind") == "roundup" else "story"
    usages: list = []
    board = None
    if mode in ("claude", "hybrid") and claude is not None:
        ok, why = claude.available()
        if not ok:
            decisions.append({"stage": "direction", "provider": "claude", "used": False, "reason": why, "fallback": "ollama/template"})
        else:
            count = len(topic["repos"]) if fmt == "roundup" else int(settings.model_extra.get("story_points", 4))
            allowed = min(settings.cinematic.max_scenes, settings.budget.max_higgsfield_scenes) if (mode == "hybrid" and settings.cinematic.enabled) else 0
            try:
                board, usages = claude.direct(research_packet, topic=topic, sources=sources, fmt=fmt, scene_count=count + 2,
                                              target_seconds=settings.production.target_duration_seconds,
                                              cinematic_allowed=allowed, video_id=video_id, gate=gate)
                decisions.append({"stage": "direction", "provider": "claude", "model": board.director.get("model"), "used": True,
                                  "cinematic_allowed": allowed})
            except ProviderError as exc:
                decisions.append({"stage": "direction", "provider": "claude", "used": False, "reason": exc.message,
                                  "error_kind": exc.kind, "fallback": "ollama/template"})
            except Exception as exc:   # budget/approval gate refusals surface here
                decisions.append({"stage": "direction", "provider": "claude", "used": False, "reason": str(exc)[:300],
                                  "error_kind": type(exc).__name__, "fallback": "ollama/template"})
    if board is None:
        result = script_locally(topic, settings, decisions)
        board = from_plan(result.plan, video_id=video_id, fmt=fmt, topic=topic,
                          director={"provider": "local", "script_provider": result.provider, "model": result.model, "created_at": time.time(),
                                    "interactive": False})
        board.sources = sources or board.sources
        if fmt == "roundup":
            board.repos = topic.get("repos", [])
        board.creative_direction.audience = "developers and AI builders"
        board.creative_direction.core_message = board.scenes[0].narration[:240]
        board.creative_direction.call_to_action = board.scenes[-1].narration[:160]
    board.seed = seed
    board = local_direction(board, settings, seed, cinematic) if board.director.get("provider") == "local" else _fill_missing(board, settings)
    report = research.verify(board, topic)
    return Storyboard.model_validate(board.model_dump()), report, usages


def _fill_missing(board: Storyboard, settings) -> Storyboard:
    for scene in board.scenes:
        if scene.character is None:
            scene.character = scene.role in ("hook", "outro")
        if scene.layout:
            scene.layout = scene.layout if scene.layout in semantic_router.CATALOG else ""
    return board
