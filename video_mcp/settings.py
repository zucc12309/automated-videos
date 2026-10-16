"""Typed, backward-compatible view of config.json.

The original flat keys (model, voice, fps, music, ...) stay authoritative. V2 adds optional nested sections; anything
missing falls back to safe defaults: LOCAL mode, no paid generation, explicit approval.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ROOT = Path(__file__).resolve().parents[1]

Mode = Literal["local", "claude", "hybrid"]
ApprovalPolicy = Literal["explicit", "auto_within_budget", "deny"]

# Aliases are resolved to verified provider identifiers. Only IDs confirmed against Anthropic's model table
# (cached 2026-10-06) are listed; anything else must be a full model ID and is passed through unchanged.
CLAUDE_MODEL_ALIASES = {
    "opus-5.5": "claude-opus-5-5", "opus": "claude-opus-5-5", "claude-opus-5.5": "claude-opus-5-5",
    "sonnet-5.5": "claude-sonnet-5-5", "sonnet": "claude-sonnet-5-5",
    "haiku-5.5": "claude-haiku-5-5", "haiku": "claude-haiku-5-5",
}


class _Section(BaseModel):
    model_config = ConfigDict(extra="allow")


class Production(_Section):
    mode: Mode = "local"
    quality: Literal["draft", "standard", "premium"] = "premium"
    target_duration_seconds: float = Field(default=40, ge=8, le=180)
    theme: str = "fieldnotes-premium"          # V2.2 production default; "auto" = seeded legacy themes
    style: Literal["premium", "studio"] = "premium"   # premium = FIELDNOTES renderer; studio = V2 renderer
    character: Literal["auto", "on", "off"] = "auto"
    resolution: tuple[int, int] | None = None   # None -> legacy width/height keys
    fps: int | None = None


class CreativeDirector(_Section):
    provider: Literal["ollama", "claude", "template"] = "ollama"
    preferred_claude_model: str = "opus-5.5"
    fallback_provider: Literal["ollama", "template"] = "ollama"
    max_revisions: int = Field(default=2, ge=0, le=5)
    max_output_tokens: int = Field(default=12000, ge=1000, le=64000)
    effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium"
    timeout_seconds: float = 240


class Cinematic(_Section):
    enabled: bool = False
    provider: Literal["higgsfield", "higgsfield_mcp", "mock"] = "higgsfield"   # higgsfield_mcp = footage via the agent's MCP
    application: str = ""          # Higgsfield application/endpoint id; must be set explicitly, never guessed
    model_label: str = ""          # human-readable model name for provenance
    max_scenes: int = Field(default=2, ge=0, le=8)
    max_duration_seconds: float = Field(default=8, ge=0, le=60)
    cache_assets: bool = True
    usd_per_second_upper_bound: float | None = None   # user-verified conservative price; None = unknown
    poll_interval_seconds: float = 5
    timeout_seconds: float = 900
    max_download_mb: int = 300
    mcp_model: str = "seedance_2_0"                  # recommended Higgsfield model for plan_footage (agent-brokered)
    mcp_params: dict = Field(default_factory=lambda: {"mode": "fast", "resolution": "720p", "generate_audio": False})
    mcp_duration_range: tuple[float, float] = (4, 15)


class Brand(_Section):
    wordmark: str = "FIELDNOTES"
    public_character_name: str | None = None   # never rendered unless approved and set
    cta_dm_delivery_enabled: bool = False      # only an authorized, working delivery integration may set this


class Budget(_Section):
    allow_paid_generation: bool = False
    approval_policy: ApprovalPolicy = "explicit"
    on_missing_approval: Literal["fallback", "pause"] = "fallback"
    max_usd_per_video: float = Field(default=1.0, ge=0)
    max_usd_per_day: float = Field(default=5.0, ge=0)
    max_claude_calls_per_video: int = Field(default=3, ge=0)
    max_higgsfield_scenes: int = Field(default=2, ge=0)
    max_higgsfield_duration_seconds: float = Field(default=8, ge=0)


class QualityControl(_Section):
    enabled: bool = True
    max_repairs: int = Field(default=2, ge=0, le=5)
    require_technical_pass: bool = True
    vision_review: bool = False


class Narration(_Section):
    engine: Literal["auto", "kokoro", "espeak"] = "auto"
    espeak_voice: str = "en-us"
    pronunciations: dict[str, str] = Field(default_factory=dict)
    expand_acronyms: bool = True
    audio_profile: Literal["reference", "off"] = "reference"   # brand/audio_profile.json (Reference A); "off" = V2 sound


class Renderer(_Section):
    browser_executable: str = ""
    concurrency: int = Field(default=2, ge=1, le=16)
    timeout_seconds: int = 1800


class Settings(BaseModel):
    model_config = ConfigDict(extra="allow")
    # Legacy flat keys (unchanged meaning)
    model: str = "qwen2.5:14b"
    voice: str = "am_adam"
    tts_language_code: str = "a"
    fps: int = 30
    width: int = 1080
    height: int = 1920
    music: bool = True
    voice_speed: float = 1.0
    brand: str = "FIELDNOTES"
    styles: list[str] = Field(default_factory=lambda: ["studio"])
    # V2 sections
    production: Production = Field(default_factory=Production)
    creative_director: CreativeDirector = Field(default_factory=CreativeDirector)
    cinematic: Cinematic = Field(default_factory=Cinematic)
    budget: Budget = Field(default_factory=Budget)
    quality_control: QualityControl = Field(default_factory=QualityControl)
    narration: Narration = Field(default_factory=Narration)
    renderer: Renderer = Field(default_factory=Renderer)
    brand_profile: Brand = Field(default_factory=Brand)

    @model_validator(mode="before")
    @classmethod
    def migrate(cls, raw: dict):
        """Accept the V1 flat file and the example 'production' block from the V2 brief (which mixes budget keys in)."""
        raw = dict(raw or {})
        production = dict(raw.get("production") or {})
        budget = dict(raw.get("budget") or {})
        moves = {"allow_paid_generation": "allow_paid_generation", "approval_policy": "approval_policy",
                 "max_cost_usd_per_video": "max_usd_per_video", "max_cost_usd_per_day": "max_usd_per_day",
                 "max_higgsfield_scenes": "max_higgsfield_scenes", "max_higgsfield_duration_seconds": "max_higgsfield_duration_seconds",
                 "max_claude_calls_per_video": "max_claude_calls_per_video"}
        for old, new in moves.items():
            if old in production:
                budget.setdefault(new, production.pop(old))
        if "max_visual_repair_attempts" in production:
            qc = dict(raw.get("quality_control") or {})
            qc.setdefault("max_repairs", production.pop("max_visual_repair_attempts"))
            raw["quality_control"] = qc
        raw["production"], raw["budget"] = production, budget
        return raw

    @property
    def size(self) -> tuple[int, int]:
        return tuple(self.production.resolution) if self.production.resolution else (self.width, self.height)

    @property
    def frame_rate(self) -> int:
        return self.production.fps or self.fps

    def claude_model(self) -> str:
        alias = self.creative_director.preferred_claude_model.strip()
        return CLAUDE_MODEL_ALIASES.get(alias.lower(), alias)

    def browser(self) -> str:
        return os.environ.get("REMOTION_BROWSER_EXECUTABLE") or self.renderer.browser_executable


def load(path: Path | None = None) -> Settings:
    return Settings.model_validate(json.loads((path or ROOT / "config.json").read_text()))


def from_dict(raw: dict) -> Settings:
    return Settings.model_validate(raw)
