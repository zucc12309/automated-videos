"""Versioned storyboard schema (V2) with migration from the V1 `Plan` scene format.

Model-generated JSON is never trusted: Claude/Ollama fill `DirectorOutput` (a constraint-free schema that structured
outputs can enforce), which is then validated into `Storyboard` here with length limits, claim checks and safe defaults.
"""
from __future__ import annotations

import hashlib
import re
import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "2.0"

Intent = Literal["hook", "product_intro", "api_flow", "repository", "comparison", "process", "architecture", "code",
                 "growth", "statistic", "app_demo", "real_world", "timeline", "warning", "quote", "list", "recap", "generic"]
INTENTS: tuple[str, ...] = Intent.__args__  # type: ignore[attr-defined]
Role = Literal["hook", "item", "body", "outro"]
Engine = Literal["remotion", "cinematic"]
Pace = Literal["emphasis", "medium", "demonstration", "pause", "montage"]
Enter = Literal["fade", "slide", "scale", "mask", "reveal"]
Emphasize = Literal["pulse", "zoom", "highlight", "underline", "counter", "none"]
Connect = Literal["line_draw", "node_link", "flow", "morph", "none"]
Exit = Literal["fade", "push", "mask", "collapse", "cut"]
Camera = Literal["static", "subtle_push", "pan_left", "pan_right", "parallax", "dolly"]
THEMES = ("fieldnotes-premium", "carbon", "midnight", "warm-editorial", "minimal-white", "tech-mono", "soft-gradient", "product-launch", "cinematic-dark")


class Source(BaseModel):
    id: str = Field(max_length=16)
    url: str = Field(max_length=500)
    title: str = Field(default="", max_length=250)
    kind: Literal["article", "repository", "feed", "manual", "api"] = "article"
    retrieved_at: float = Field(default_factory=time.time)


class Claim(BaseModel):
    id: str = Field(max_length=16)
    text: str = Field(max_length=400)
    source_ids: list[str] = Field(default_factory=list)
    status: Literal["verified", "interpretation", "unverified", "removed"] = "unverified"
    note: str = Field(default="", max_length=300)


class Motion(BaseModel):
    entrance: Enter = "reveal"
    emphasis: Emphasize = "highlight"
    connect: Connect = "none"
    exit: Exit = "cut"
    camera: Camera = "subtle_push"
    intensity: float = Field(default=1.0, ge=0, le=1.6)
    stagger_frames: int = Field(default=4, ge=0, le=12)


class CinematicSpec(BaseModel):
    prompt: str = Field(max_length=900)
    duration_seconds: float = Field(default=4, ge=1, le=15)
    negative_guidance: list[str] = Field(default_factory=lambda: ["unreadable text", "random logos", "watermarks",
                                                                   "excessive camera shake", "distorted hands"])
    reference_images: list[str] = Field(default_factory=list, max_length=4)
    overlay_text: bool = True          # accurate text is composited by Remotion, never generated in-video
    fallback_layout: str = "heroWord"


class Asset(BaseModel):
    kind: Literal["cinematic", "image", "audio", "graphic"]
    path: str = Field(max_length=400)          # relative to public/
    sha256: str = Field(default="", max_length=64)
    provider: str = Field(default="", max_length=40)
    provenance: dict = Field(default_factory=dict)


class SceneQA(BaseModel):
    status: Literal["pending", "pass", "fail", "repaired", "fallback"] = "pending"
    issues: list[str] = Field(default_factory=list)
    repairs: int = 0


class Visual(BaseModel):
    """Structured content for semantic layouts. All text is shown on screen and must be short."""
    code: list[str] = Field(default_factory=list, max_length=10)
    code_language: str = Field(default="", max_length=20)
    steps: list[str] = Field(default_factory=list, max_length=5)
    compare_left: list[str] = Field(default_factory=list, max_length=4)
    compare_right: list[str] = Field(default_factory=list, max_length=4)
    compare_titles: list[str] = Field(default_factory=list, max_length=2)
    series_labels: list[str] = Field(default_factory=list, max_length=6)
    series_values: list[float] = Field(default_factory=list, max_length=6)
    timeline: list[str] = Field(default_factory=list, max_length=5)
    nodes: list[str] = Field(default_factory=list, max_length=6)
    url: str = Field(default="", max_length=80)       # display-only address for browser mockups
    prompt_before: list[str] = Field(default_factory=list, max_length=5)   # weak prompt (vibe coding), shown then transformed
    prompt_after: list[str] = Field(default_factory=list, max_length=5)    # improved prompt

    @field_validator("code")
    @classmethod
    def short_lines(cls, lines):
        return [line[:48] for line in lines]

    @field_validator("prompt_before", "prompt_after")
    @classmethod
    def prompt_lines(cls, lines):
        return [re.sub(r"\s+", " ", l).strip()[:60] for l in lines if l and l.strip()]

    @field_validator("steps", "compare_left", "compare_right", "compare_titles", "series_labels", "timeline", "nodes")
    @classmethod
    def short_labels(cls, items):
        return [re.sub(r"\s+", " ", i).strip()[:42] for i in items if i and i.strip()]


class StoryScene(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(pattern=r"^scene_\d{3}$")
    role: Role = "body"
    narration: str = Field(min_length=1, max_length=500)
    heading: str = Field(min_length=1, max_length=65)
    points: list[str] = Field(default_factory=list, max_length=3)
    emphasis: str = Field(default="", max_length=30)
    stat: str = Field(default="", max_length=20)
    label: str = Field(default="", max_length=28)
    item: int = Field(default=0, ge=0, le=8)
    visual_intent: str = Field(default="", max_length=160)
    intent: Intent = "generic"
    render_engine: Engine = "remotion"
    layout: str = Field(default="", max_length=24)      # optional preferred layout; router may override if unfit
    motion: Motion = Field(default_factory=Motion)
    pace: Pace = "medium"
    priority: Literal["high", "normal", "low"] = "normal"
    estimated_duration: float = Field(default=0, ge=0, le=30)
    claim_ids: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    visual: Visual = Field(default_factory=Visual)
    cinematic: CinematicSpec | None = None
    assets: list[Asset] = Field(default_factory=list)
    character: bool | None = None                       # None = theme decides
    character_action: Literal["", "idle", "speaking", "thinking", "pointing", "typing", "explaining", "surprised", "celebrating", "warning",
                              "confused", "presenting"] = ""   # director override for the character's state in this scene
    cta: dict = Field(default_factory=dict)              # outro only: {keyword, secondary, fulfillment}
    fallback_layout: str = Field(default="heroWord", max_length=24)
    qa: SceneQA = Field(default_factory=SceneQA)

    @model_validator(mode="after")
    def grounded_highlights(self):
        if re.search(r"https?://|www\.", self.narration):
            raise ValueError("Keep URLs in sources, not narration")
        if self.emphasis.strip().lower() not in self.narration.lower():
            self.emphasis = ""
        if not re.search(r"\d", self.stat) or self.stat.strip() not in self.narration:
            self.stat = ""
        self.points = [p[:65] for p in self.points]
        if self.render_engine == "cinematic" and self.cinematic is None:
            self.render_engine = "remotion"
        return self


class CreativeDirection(BaseModel):
    audience: str = Field(default="developers", max_length=160)
    core_message: str = Field(default="", max_length=240)
    viewer_benefit: str = Field(default="", max_length=240)
    hook: str = Field(default="", max_length=160)
    tone: str = Field(default="premium editorial", max_length=60)
    pacing: Literal["calm", "measured", "dynamic", "rapid"] = "dynamic"
    theme: str = Field(default="carbon", max_length=24)
    visual_identity: str = Field(default="minimal technology", max_length=120)
    sound_design: str = Field(default="restrained UI accents under narration", max_length=200)
    call_to_action: str = Field(default="", max_length=160)
    character: Literal["auto", "on", "off"] = "auto"

    @field_validator("theme")
    @classmethod
    def known_theme(cls, value):
        return value if value in THEMES else "carbon"


class Storyboard(BaseModel):
    schema_version: Literal["2.0"] = SCHEMA_VERSION
    video_id: str = Field(default="", max_length=40)
    title: str = Field(min_length=1, max_length=100)
    format: Literal["story", "roundup", "explainer", "vibe_coding"] = "explainer"
    duration_target_seconds: float = Field(default=40, ge=8, le=180)
    aspect_ratio: Literal["9:16", "16:9", "1:1", "4:5"] = "9:16"
    series: str = Field(default="", max_length=16)
    creative_direction: CreativeDirection = Field(default_factory=CreativeDirection)
    sources: list[Source] = Field(default_factory=list, max_length=12)
    claims: list[Claim] = Field(default_factory=list, max_length=40)
    scenes: list[StoryScene] = Field(min_length=2, max_length=10)
    repos: list[dict] = Field(default_factory=list, max_length=8)
    director: dict = Field(default_factory=dict)       # provider, model, created_at, interactive flag
    seed: str = Field(default="", max_length=40)
    hook_candidates: list[dict] = Field(default_factory=list, max_length=6)   # scored alternatives; the chosen one is scene_001
    cta: dict = Field(default_factory=dict)                                    # {keyword, secondary, narration, fulfillment, resources}

    @model_validator(mode="after")
    def integrity(self):
        ids = [s.id for s in self.scenes]
        if len(set(ids)) != len(ids):
            raise ValueError("Scene ids must be unique")
        known_claims = {c.id for c in self.claims}
        known_sources = {s.id for s in self.sources}
        for claim in self.claims:
            claim.source_ids = [s for s in claim.source_ids if s in known_sources]
            if claim.status == "verified" and not claim.source_ids:
                claim.status = "unverified"
        for scene in self.scenes:
            scene.claim_ids = [c for c in scene.claim_ids if c in known_claims]
            scene.depends_on = [d for d in scene.depends_on if d in ids and d != scene.id]
        if re.search(r"[ऀ-ॿ]", " ".join(s.narration for s in self.scenes) + self.title):
            raise ValueError("Video copy must be in English only")
        return self

    def fingerprint(self) -> str:
        return hashlib.sha256(self.model_dump_json(exclude={"director", "video_id"}).encode()).hexdigest()[:16]


# ---------- Model-facing schema (no numeric/string constraints; every field required) ----------

class DirectorScene(BaseModel):
    model_config = ConfigDict(extra="forbid")
    narration: str
    heading: str
    points: list[str]
    emphasis: str
    stat: str
    label: str
    visual_intent: str
    intent: Intent
    render_engine: Engine
    layout: str
    entrance: Enter
    emphasis_motion: Emphasize
    camera: Camera
    pace: Pace
    claim_ids: list[str]
    code_lines: list[str]
    steps: list[str]
    compare_titles: list[str]
    compare_left: list[str]
    compare_right: list[str]
    nodes: list[str]
    timeline: list[str]
    cinematic_prompt: str
    character: bool
    prompt_before: list[str] = Field(default_factory=list)
    prompt_after: list[str] = Field(default_factory=list)


class DirectorClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    text: str
    source_ids: list[str]
    status: Literal["verified", "interpretation", "unverified"]


class DirectorOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    series: str
    audience: str
    core_message: str
    viewer_benefit: str
    hook: str
    tone: str
    pacing: Literal["calm", "measured", "dynamic", "rapid"]
    theme: Literal["carbon", "midnight", "warm-editorial", "minimal-white", "tech-mono", "soft-gradient", "product-launch", "cinematic-dark"]
    visual_identity: str
    sound_design: str
    call_to_action: str
    claims: list[DirectorClaim]
    scenes: list[DirectorScene]


_UNSUPPORTED = {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf", "minLength", "maxLength",
                "minItems", "maxItems", "pattern", "default", "title"}


def strict_json_schema(model: type[BaseModel]) -> dict:
    """Pydantic schema -> structured-output-compatible schema (no unsupported constraints, closed objects)."""
    def clean(node):
        if isinstance(node, dict):
            out = {k: clean(v) for k, v in node.items() if k not in _UNSUPPORTED}
            if out.get("type") == "object" or "properties" in out:
                out["additionalProperties"] = False
                out["required"] = list(out.get("properties", {}).keys())
            return out
        if isinstance(node, list):
            return [clean(v) for v in node]
        return node
    return clean(model.model_json_schema())


def _scene_id(i: int) -> str:
    return f"scene_{i + 1:03d}"


def from_director(out: DirectorOutput, *, topic: dict, sources: list[Source], fmt: str, target: float,
                  director: dict, video_id: str = "") -> Storyboard:
    """Validate model output into a Storyboard. Invalid optional details are dropped rather than trusted."""
    n = len(out.scenes)
    scenes = []
    for i, s in enumerate(out.scenes[:10]):
        role: Role = "hook" if i == 0 else "outro" if i == n - 1 else ("item" if fmt in ("roundup", "story") else "body")
        cinematic = None
        if s.render_engine == "cinematic" and s.cinematic_prompt.strip():
            cinematic = CinematicSpec(prompt=s.cinematic_prompt.strip()[:900], fallback_layout=s.layout or "heroWord")
        visual = Visual(code=s.code_lines, steps=s.steps, compare_titles=s.compare_titles, compare_left=s.compare_left,
                        compare_right=s.compare_right, nodes=s.nodes, timeline=s.timeline, prompt_before=s.prompt_before, prompt_after=s.prompt_after)
        scenes.append(StoryScene(
            id=_scene_id(i), role=role, narration=s.narration.strip()[:500], heading=(s.heading.strip() or s.label or "Key idea")[:65],
            points=[p.strip()[:65] for p in s.points if p.strip()][:3], emphasis=s.emphasis.strip()[:30], stat=s.stat.strip()[:20],
            label=s.label.strip()[:28], item=i if role == "item" else 0, visual_intent=s.visual_intent[:160], intent=s.intent,
            render_engine=s.render_engine if cinematic else "remotion", layout=s.layout[:24],
            motion=Motion(entrance=s.entrance, emphasis=s.emphasis_motion, camera=s.camera), pace=s.pace,
            claim_ids=s.claim_ids, visual=visual, cinematic=cinematic, character=s.character))
    claims = [Claim(id=c.id[:16], text=c.text[:400], source_ids=c.source_ids, status=c.status) for c in out.claims[:40]]
    cd = CreativeDirection(audience=out.audience[:160], core_message=out.core_message[:240], viewer_benefit=out.viewer_benefit[:240],
                           hook=out.hook[:160], tone=out.tone[:60], pacing=out.pacing, theme=out.theme,
                           visual_identity=out.visual_identity[:120], sound_design=out.sound_design[:200],
                           call_to_action=out.call_to_action[:160])
    return Storyboard(video_id=video_id, title=out.title.strip()[:100] or topic.get("title", "Untitled")[:100], format=fmt,
                      duration_target_seconds=target, series=re.sub(r"[^A-Z]", "", out.series.upper())[:16],
                      creative_direction=cd, sources=sources, claims=claims, scenes=scenes,
                      repos=topic.get("repos", []) if fmt == "roundup" else [], director=director)


def from_plan(plan, *, video_id: str = "", fmt: str | None = None, director: dict | None = None, topic: dict | None = None) -> Storyboard:
    """Migrate a V1 Plan (or plan dict) into a Storyboard. Intents are inferred later by the semantic router."""
    raw = plan if isinstance(plan, dict) else plan.model_dump()
    scenes_raw = raw["scenes"]
    n = len(scenes_raw)
    fmt = fmt or ("roundup" if raw.get("repos") else "story" if any(s.get("item") for s in scenes_raw) else "explainer")
    sources = [Source(id=f"src{i + 1}", url=u, kind="repository" if "github.com" in u else "article")
               for i, u in enumerate(raw.get("source_urls", [])[:12])]
    scenes = []
    for i, s in enumerate(scenes_raw):
        visual = s.get("visual", "cards")
        role: Role = "hook" if visual == "hook" or (i == 0 and n > 2 and not s.get("item")) else \
            "outro" if visual == "outro" or (i == n - 1 and n > 2 and not s.get("item")) else ("item" if s.get("item") else "body")
        # V1 visuals only hint at an intent; structural roles are certain, the rest is inferred from the words later.
        intent = "hook" if role == "hook" else "recap" if role == "outro" else "repository" if visual == "repo" else "generic"
        scenes.append(StoryScene(id=_scene_id(i), role=role, narration=s["narration"], heading=s["heading"], points=s.get("points", []),
                                 emphasis=s.get("emphasis", ""), stat=s.get("stat", ""), label=s.get("label", ""),
                                 item=s.get("item", 0), intent=intent, claim_ids=[]))
    return Storyboard(video_id=video_id, title=raw["title"], format=fmt, series=raw.get("series", ""), sources=sources,
                      scenes=scenes, repos=[dict(r) for r in raw.get("repos", [])],
                      director=director or {"provider": "plan", "model": "none", "migrated_from": "plan_v1", "created_at": time.time()})


def to_plan_dict(board: Storyboard) -> dict:
    """The V1 Plan contract consumed by narration + legacy styles (kept so plan.json stays compatible)."""
    roundup = board.format == "roundup"
    scenes = []
    for s in board.scenes:
        visual = "hook" if s.role == "hook" else "outro" if s.role == "outro" else \
            "repo" if roundup and s.item else "doc" if s.item else \
            {"code": "terminal", "process": "flow", "statistic": "meter", "growth": "meter"}.get(s.intent, "cards")
        scenes.append({"heading": s.heading, "narration": s.narration, "caption": s.narration, "points": s.points, "visual": visual,
                       "item": s.item, "label": s.label, "emphasis": s.emphasis, "stat": s.stat})
    return {"title": board.title, "scenes": scenes, "source_urls": [x.url for x in board.sources], "style": "studio",
            "series": board.series, "repos": [{k: r.get(k) for k in ("full_name", "owner", "name", "description", "stars", "language", "topics")
                                                 if k in r} for r in board.repos]}
