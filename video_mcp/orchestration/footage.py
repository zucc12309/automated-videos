"""Higgsfield through its MCP connector (agent-brokered footage).

The Higgsfield MCP server lives in the agent (Claude Code / Claude app / Codex), not in this Python process. So the
pipeline never calls Higgsfield and never spends credits. The work is split:

1. `plan(board, cfg)` → shot list: for each cinematic scene the render will use, a stable `footage_key`, a brand-styled
   9:16 prompt, the duration, and the recommended Higgsfield model and parameters (config `cinematic.mcp_model` /
   `mcp_params`).
2. The agent generates each shot with the Higgsfield MCP generate tool, only after the person approves the credit cost,
   or picks an existing clip from the person's Higgsfield history (`show_generations`).
3. `attach(key, url | file)` downloads (https, SSRF-checked, size-capped), decodes and validates the clip, and stores it in
   the content-addressed asset cache under that key with Higgsfield provenance (generation id, model, credits).
4. The render finds the clip as a cache hit for that scene. Shots without footage fall back to Remotion graphics, and the
   fallback is recorded.

The request and key are built by the same functions the pipeline uses, so planning and rendering agree.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

from .. import security
from ..providers.base import CinematicRequest, CostEstimate, ProviderError
from .asset_manager import AssetManager, cache_key, probe_video

ROOT = Path(__file__).resolve().parents[2]


def _style() -> str:
    return json.loads((ROOT / "brand" / "motion.json").read_text()).get("footage_style", "")


def selected_scenes(board, cfg) -> list:
    """Same selection rule as the render: up to max_scenes cinematic scenes within the duration cap."""
    limit = min(cfg.cinematic.max_scenes, cfg.budget.max_higgsfield_scenes)
    seconds_cap = min(cfg.cinematic.max_duration_seconds, cfg.budget.max_higgsfield_duration_seconds)
    picked, total = [], 0.0
    for scene in board.scenes:
        if scene.render_engine == "cinematic" and scene.cinematic and len(picked) < limit:
            if total + scene.cinematic.duration_seconds <= seconds_cap + 1e-9:
                picked.append(scene)
                total += scene.cinematic.duration_seconds
    return picked


def request_for(scene, on_unsafe=None) -> CinematicRequest:
    spec = scene.cinematic
    refs = []
    for url in spec.reference_images:
        try:
            refs.append(security.check_url(url, resolve=False, allowed_schemes=("https",)))
        except security.UnsafeURL:
            if on_unsafe:
                on_unsafe(url)
    return CinematicRequest(scene_id=scene.id, prompt=spec.prompt, duration_seconds=spec.duration_seconds,
                            aspect_ratio="9:16", negative_guidance=spec.negative_guidance, reference_images=refs,
                            fallback=spec.fallback_layout, seed=int(hashlib.sha256(scene.id.encode()).hexdigest()[:6], 16))


def key_for(req: CinematicRequest, provider, cfg) -> str:
    caps = provider.capabilities()
    return cache_key(provider=provider.name, model=json.dumps(caps.get("model") or {}, sort_keys=True) + "|" + str(caps.get("application", "")),
                     prompt=req.prompt, params={"d": req.duration_seconds, "ar": req.aspect_ratio, "res": req.resolution,
                                                "neg": req.negative_guidance, "extra": req.params},
                     reference_hashes=[hashlib.sha256(r.encode()).hexdigest() for r in req.reference_images], seed=req.seed,
                     config={"application": cfg.cinematic.application})


class HiggsfieldMCPProvider:
    """Brokered provider: never generates. It reports which shots need footage; footage arrives via `attach`."""
    name = "higgsfield_mcp"
    brokered = True

    def __init__(self, settings):
        self.settings = settings

    def available(self) -> tuple[bool, str]:
        return True, "Higgsfield via the agent's MCP connector; footage is attached with attach_footage"

    def capabilities(self) -> dict:
        c = self.settings.cinematic
        return {"provider": self.name, "model": {"id": c.mcp_model, "params": c.mcp_params}, "application": "higgsfield-mcp",
                "brokered": True, "cost_estimate_endpoint": False}

    def validate(self, request: CinematicRequest) -> None:
        return None

    def estimate_cost(self, request: CinematicRequest) -> CostEstimate:
        return CostEstimate(usd=0.0, basis="this pipeline spends nothing; Higgsfield credits are charged in your Higgsfield account "
                                          "when the agent generates the shot through the Higgsfield MCP (after your approval)")

    def submit(self, request: CinematicRequest, idempotency_key: str) -> str:
        raise ProviderError(self.name, "not_attached", "no Higgsfield footage attached for this shot (plan_footage → attach_footage)")


def model_duration(seconds: float, cfg) -> float:
    lo, hi = cfg.cinematic.mcp_duration_range
    return float(min(max(round(seconds), lo), hi))


def plan(board, cfg, assets: AssetManager) -> dict:
    provider = HiggsfieldMCPProvider(cfg)
    style = _style()
    shots = []
    for scene in selected_scenes(board, cfg):
        req = request_for(scene)
        key = key_for(req, provider, cfg)
        hit = assets.lookup(key)
        shots.append({
            "scene_id": scene.id, "footage_key": key, "attached": bool(hit),
            "attached_generation": (hit or {}).get("generation_id"),
            "narration": scene.narration,
            "higgsfield": {"model_id": cfg.cinematic.mcp_model, "aspect_ratio": "9:16",
                           "duration_seconds": model_duration(req.duration_seconds, cfg),
                           "params": cfg.cinematic.mcp_params,
                           "prompt": f"{req.prompt.rstrip('.')}. {style}".strip(),
                           "negative": ", ".join(dict.fromkeys(req.negative_guidance + ["on-screen text", "captions", "logos", "watermarks"]))},
            "fallback_if_missing": f"remotion:{req.fallback or scene.fallback_layout}",
        })
    return {
        "provider": provider.name, "shots": shots, "missing": [s["scene_id"] for s in shots if not s["attached"]],
        "steps": [
            "Higgsfield MCP: models_get(model_id) to confirm parameters; balance to confirm credits.",
            "Tell the person the shots, model and expected credit cost; generate only after they approve.",
            "Generate each shot with the Higgsfield MCP generate tool (or pick a finished clip from show_generations).",
            "attach_footage(footage_key, video_url, generation_id, model_id, credits_used) for each result.",
            "Render: create_hybrid_video(mode='hybrid', storyboard=...). Shots without footage fall back to Remotion.",
        ],
        "note": "Plan keys depend on the storyboard's cinematic prompt/duration and cinematic.mcp_model; re-plan after editing either.",
    }


def _clean_url(url: str) -> str:
    """Provenance keeps the URL without its query string (signed CDN URLs carry tokens)."""
    return re.sub(r"[?#].*$", "", url)[:500]


def attach(assets: AssetManager, key: str, *, video_url: str = "", file_path: str = "", generation_id: str = "", model_id: str = "",
           credits_used: float | None = None, max_mb: int = 300, work_dir: Path | None = None) -> dict:
    if not re.fullmatch(r"[0-9a-f]{64}", key or ""):
        raise ValueError("footage_key must be the 64-hex key returned by plan_footage")
    if bool(video_url) == bool(file_path):
        raise ValueError("pass exactly one of video_url or file_path")
    work = work_dir or (assets.root.parent / "footage_tmp")
    work.mkdir(parents=True, exist_ok=True)
    temp = work / f"{key[:16]}-{int(time.time() * 1000)}.mp4"
    if video_url:
        AssetManager.download(video_url, temp, max_mb)
        source = _clean_url(video_url)
    else:
        src = Path(file_path).expanduser().resolve()
        if not src.is_file():
            raise ValueError(f"no such file: {src}")
        if src.stat().st_size > max_mb * 1024 * 1024:
            raise ValueError(f"file exceeds {max_mb} MB")
        temp.write_bytes(src.read_bytes())
        source = f"file:{src.name}"
    try:
        probe = probe_video(temp)
        warnings = []
        if probe["width"] and probe["height"] and probe["width"] > probe["height"]:
            warnings.append("landscape clip: it will be centre-cropped to 9:16")
        stored = assets.store(key, temp, {"provider": "higgsfield_mcp", "generation_id": generation_id[:120], "model_id": model_id[:120],
                                          "credits_used": credits_used, "source": source, "probe": probe, "attached_at": time.time(),
                                          "mock": False})
    finally:
        temp.unlink(missing_ok=True)
    return {"footage_key": key, "stored": True, "probe": probe, "warnings": warnings, "generation_id": generation_id, "sha256": stored["sha256"]}
