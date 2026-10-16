"""Synchronous helpers behind the V2 MCP tools (fast, no rendering). Long work goes through engine.start_job."""
from __future__ import annotations

import json
import re

from .. import engine, security, settings as settings_mod, tts, variety
from ..creative import director
from ..providers.claude_provider import ClaudeProvider
from ..schemas.storyboard import Storyboard, from_plan
from .asset_manager import AssetManager
from .cost_controller import CostController, claude_upper_bound

WORDS_PER_SECOND = 2.6


def _cfg():
    return settings_mod.load(engine.ROOT / "config.json")


def _board(plan: dict | None, storyboard: dict | None, seed: str) -> Storyboard:
    if storyboard:
        board = Storyboard.model_validate(storyboard)
        board.seed = board.seed or seed
        return board
    board = from_plan(engine.Plan.model_validate(plan).model_dump())
    board.seed = seed
    return director.local_direction(board, _cfg(), seed)


def layout_preview(board: Storyboard) -> list[dict]:
    """Plan layouts with estimated speech timing (2.6 words/s) — the same router the renderer uses."""
    scenes = []
    for s in board.scenes:
        words, t = [], 0.0
        for w in s.narration.split():
            length = max(.16, .055 * len(re.sub(r"\W", "", w)) + .1)     # ~2.6 words/s for average English words
            words.append({"w": w, "s": round(t, 2), "e": round(t + length, 2)})
            t += length + (.22 if re.search(r"[.,!?;:]$", w) else .03)
        lo, hi = variety.PACE.get(s.pace, (1.3, 3.0))
        scenes.append({"id": s.id, "visual": "hook" if s.role == "hook" else "outro" if s.role == "outro" else
                       ("repo" if board.format == "roundup" and s.item else "doc" if s.item else "cards"),
                       "item": s.item, "role": s.role, "intent": s.intent, "narration": s.narration, "points": s.points, "heading": s.heading,
                       "emphasis": s.emphasis, "stat": s.stat, "label": s.label, "words": words, "beats": variety.split_beats(words, t + .3, lo, hi),
                       "visualData": s.visual.model_dump(), "media": "planned" if s.render_engine == "cinematic" else None,
                       "layoutHint": s.layout, "character": bool(s.character), "_roundup": board.format == "roundup", "seconds": t + .3})
    variant = {"seed": board.seed or "preview", "transitions": ["push", "mask", "cut"], "theme": board.creative_direction.theme, "character": True}
    variety.plan_layouts(scenes, variant)
    return scenes


def preview_storyboard(plan: dict | None = None, storyboard: dict | None = None, mode: str | None = None) -> dict:
    cfg = _cfg()
    mode = mode or cfg.production.mode
    board = _board(plan, storyboard, "preview")
    scenes = layout_preview(board)
    try:
        engine_name, why = tts.available_engine(cfg.narration.engine)
    except RuntimeError as exc:
        engine_name, why = "none", str(exc)
    return {
        "title": board.title, "format": board.format, "theme": board.creative_direction.theme, "mode": mode,
        "estimated_duration_seconds": round(sum(s["seconds"] + .28 for s in scenes), 1),
        "scenes": [{"id": s["id"], "role": s["role"], "intent": s["intent"], "narration": s["narration"],
                    "estimated_seconds": round(s["seconds"], 1), "render_engine": "cinematic" if s["media"] else "remotion",
                    "beats": [{"text": b["text"], "layout": b["layout"], "why": b.get("layoutReason", {})} for b in s["beats"]]}
                   for s in scenes],
        "providers": {"direction": "supplied" if storyboard else "local heuristic director (plan supplied)",
                      "narration": f"{engine_name} ({why})", "renderer": "Remotion (local)",
                      "cinematic": "Higgsfield (gated by budget/approval)" if mode == "hybrid" and cfg.cinematic.enabled else "none"},
        "storyboard": board.model_dump(),
        "note": "Timing is estimated from word counts; the render uses real narration timing.",
    }


def estimate_video_cost(job_id: str | None = None, storyboard: dict | None = None, mode: str | None = None) -> dict:
    cfg = _cfg()
    mode = mode or cfg.production.mode
    if job_id:
        folder = engine.job_path(job_id)
        est = json.loads((folder / "estimate.json").read_text()) if (folder / "estimate.json").exists() else None
        return {"job_id": job_id, "estimate": est, "ledger": CostController(engine.DATA, cfg).job_report(job_id),
                "note": None if est else "No estimate yet; run a dry run (create_hybrid_video dry_run=true) first."}
    rows, unknown = [], False
    claude = None
    if mode in ("claude", "hybrid") and not storyboard:
        model = cfg.claude_model()
        per_call = claude_upper_bound(model, 30000, cfg.creative_director.max_output_tokens)
        calls = min(cfg.budget.max_claude_calls_per_video, cfg.creative_director.max_revisions + 1)
        claude = {"model": model, "upper_bound_usd_per_call": per_call, "max_calls": calls,
                  "upper_bound_usd": round((per_call or 0) * calls, 4) if per_call is not None else None,
                  "available": ClaudeProvider(cfg).available()[1]}
        unknown |= per_call is None
    if mode == "hybrid" and storyboard and cfg.cinematic.enabled:
        board = Storyboard.model_validate(storyboard)
        rate = cfg.cinematic.usd_per_second_upper_bound
        for s in board.scenes:
            if s.render_engine == "cinematic" and s.cinematic:
                usd = round(rate * s.cinematic.duration_seconds, 4) if rate is not None else None
                unknown |= usd is None
                rows.append({"scene": s.id, "seconds": s.cinematic.duration_seconds, "usd": usd})
    total = None if unknown else round(((claude or {}).get("upper_bound_usd") or 0) + sum(r["usd"] for r in rows), 4)
    return {"mode": mode, "claude": claude, "cinematic": rows, "total_upper_bound_usd": total,
            "uncertainty": "unknown — a provider has no verified price; explicit approval with a USD cap is required" if unknown
            else "upper bound (conservative token and per-second assumptions)",
            "local_cost_usd": 0.0, "caps": {"per_video": cfg.budget.max_usd_per_video, "per_day": cfg.budget.max_usd_per_day},
            "paid_generation_enabled": cfg.budget.allow_paid_generation, "approval_policy": cfg.budget.approval_policy}


def approve_generation(job_id: str, max_usd: float, request_id: str | None = None, resume: bool = True) -> dict:
    cfg = _cfg()
    folder = engine.job_path(job_id)
    approvals = CostController(engine.DATA, cfg).approve(folder, request_id, max_usd)
    result = {"job_id": job_id, "approved": request_id or "job budget", "max_usd": max_usd, "approvals": approvals,
              "paid_generation_enabled": cfg.budget.allow_paid_generation}
    if not cfg.budget.allow_paid_generation:
        result["warning"] = "budget.allow_paid_generation is false in config.json; no paid call will be made until it is enabled."
    status = engine.status(job_id)
    if resume and status["state"] in ("awaiting_approval", "failed"):
        result["resume"] = engine.resume_job(job_id)
    return result


def list_assets(limit: int = 50) -> dict:
    from .motion_library import MotionLibrary
    return {"assets": AssetManager(engine.DATA).list(max(1, min(limit, 200))), "motion_clips": MotionLibrary(engine.DATA).list()[:limit]}


def video_report(job_id: str) -> dict:
    folder = engine.job_path(job_id)
    read = lambda name: json.loads((folder / name).read_text()) if (folder / name).exists() else None
    board = read("storyboard.json")
    qa = read("qa/summary.json")
    return security.redact({
        "status": engine.status(job_id), "creative_direction": (board or {}).get("creative_direction"),
        "scenes": [{"id": s["id"], "role": s["role"], "intent": s["intent"], "render_engine": s["render_engine"], "qa": s["qa"],
                    "claim_ids": s["claim_ids"]} for s in (board or {}).get("scenes", [])],
        "sources": (board or {}).get("sources"), "claims": (board or {}).get("claims"), "verification": read("verification.json"),
        "decisions": read("decisions.json"), "costs": read("costs.json"), "estimate": read("estimate.json"),
        "qa": qa, "qa_report": str(folder / "qa" / "summary.md") if qa else None, "repairs": read("qa/repairs.json"),
        "provenance": read("provenance.json"), "timings": read("timings.json"), "approvals": read("approvals.json"),
        "files": sorted(str(p.relative_to(folder)) for p in folder.rglob("*") if p.is_file() and "frames" not in p.parts)[:80],
    })
