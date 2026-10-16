"""Provider interfaces and error classification shared by script, creative-direction and cinematic providers."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

ErrorKind = Literal["unavailable", "auth", "rate_limit", "invalid_output", "timeout", "budget", "approval_required",
                    "refused", "bad_request", "unknown_outcome", "server"]
RETRYABLE = {"rate_limit", "timeout", "server", "unavailable"}


class ProviderError(RuntimeError):
    def __init__(self, provider: str, kind: ErrorKind, message: str, *, retry_after: float | None = None, request_id: str | None = None):
        super().__init__(f"{provider}: {kind}: {message}")
        self.provider, self.kind, self.message, self.retry_after, self.request_id = provider, kind, message, retry_after, request_id

    @property
    def retryable(self) -> bool:
        return self.kind in RETRYABLE

    def as_dict(self) -> dict:
        return {"provider": self.provider, "kind": self.kind, "message": self.message[:500], "retryable": self.retryable,
                "request_id": self.request_id}


@dataclass
class Usage:
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float = 0.0
    estimated: bool = False
    request_id: str | None = None
    seconds: float = 0.0


@dataclass
class ScriptResult:
    """A validated engine.Plan plus how it was produced."""
    plan: Any
    provider: str
    model: str
    attempts: int = 1
    usage: list[Usage] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class ScriptProvider(Protocol):
    name: str

    def available(self) -> tuple[bool, str]: ...

    def write_plan(self, topic: dict, count: int) -> ScriptResult: ...


@dataclass
class CinematicRequest:
    scene_id: str
    prompt: str
    duration_seconds: float
    aspect_ratio: str = "9:16"
    purpose: str = "cinematic_broll"
    negative_guidance: list[str] = field(default_factory=list)
    reference_images: list[str] = field(default_factory=list)
    resolution: str = "720p"
    seed: int | None = None
    fallback: str = ""
    params: dict = field(default_factory=dict)


@dataclass
class CostEstimate:
    usd: float | None            # None = provider cannot estimate
    basis: str
    upper_bound: bool = True
    credits: float | None = None


class CinematicProvider(Protocol):
    name: str

    def capabilities(self) -> dict: ...

    def estimate_cost(self, request: CinematicRequest) -> CostEstimate: ...

    def submit(self, request: CinematicRequest, idempotency_key: str) -> str: ...

    def get_status(self, remote_id: str) -> str: ...      # queued|in_progress|completed|failed|nsfw|canceled

    def fetch_result(self, remote_id: str) -> dict: ...   # {"video_url": ..., "raw": ...}
