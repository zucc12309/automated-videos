"""Claude creative director over the official Anthropic Python SDK (runtime automation path).

Credentials: only an explicitly configured `ANTHROPIC_API_KEY` (or `ANTHROPIC_AUTH_TOKEN`) is used. The base URL is pinned
to `VIDEO_MCP_ANTHROPIC_BASE_URL` or the public API, so an interactive Claude Code session's proxy/base URL is never
silently reused for unattended jobs.
"""
from __future__ import annotations

import json
import os
import re
import time

from .. import security
from ..creative import prompts_v2
from ..schemas.storyboard import DirectorOutput, Source, Storyboard, from_director, strict_json_schema
from .base import ProviderError, Usage

DEFAULT_BASE_URL = "https://api.anthropic.com"
FALLBACK_BETA = "server-side-fallback-2026-07-01"


def _numbers(text: str) -> list[str]:
    return [n.rstrip(".,") for n in re.findall(r"\d[\d,.]*", text)]


def grounding_problems(board: Storyboard, research_text: str, cinematic_allowed: int) -> list[str]:
    """Deterministic checks Claude's draft must pass; failures are sent back as a revision request."""
    problems = []
    source_digits = {re.sub(r",", "", n).rstrip(".") for n in re.findall(r"\d[\d,.]*", research_text)}
    for s in board.scenes:
        bad = [n for n in _numbers(s.narration) if re.sub(r",", "", n) not in source_digits and not (n.isdigit() and int(n) <= 10)]
        if bad:
            problems.append(f"{s.id}: numbers not in the research data: {', '.join(bad)}")
        if not s.emphasis:
            problems.append(f"{s.id}: emphasis must be copied exactly from its narration")
        if s.render_engine == "cinematic" and s.intent in ("code", "api_flow", "statistic", "growth", "repository", "comparison"):
            problems.append(f"{s.id}: cinematic footage is not allowed for {s.intent}; render it in Remotion")
    cinematic = [s.id for s in board.scenes if s.render_engine == "cinematic"]
    if len(cinematic) > cinematic_allowed:
        problems.append(f"Too many cinematic scenes ({len(cinematic)}); at most {cinematic_allowed}")
    if board.scenes[0].role != "hook" or len(board.scenes[0].narration.split()) > 18:
        problems.append("scene_001 must be a hook of at most 14 words")
    return problems


class ClaudeProvider:
    name = "claude"

    def __init__(self, settings, client=None):
        self.settings = settings
        self.model = settings.claude_model()
        self._client = client

    def available(self) -> tuple[bool, str]:
        if self._client is not None:
            return True, "injected client"
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False, "Python package 'anthropic' is not installed (pip install anthropic)"
        if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
            return False, "ANTHROPIC_API_KEY is not set; Claude runtime direction needs an API key (a Claude subscription is not API access)"
        return True, "api key configured"

    def client(self):
        if self._client is None:
            import anthropic
            ok, why = self.available()
            if not ok:
                raise ProviderError(self.name, "auth", why)
            kwargs = {"base_url": os.environ.get("VIDEO_MCP_ANTHROPIC_BASE_URL", DEFAULT_BASE_URL),
                      "timeout": self.settings.creative_director.timeout_seconds, "max_retries": 2}
            if os.environ.get("ANTHROPIC_API_KEY"):
                kwargs["api_key"] = os.environ["ANTHROPIC_API_KEY"]
            else:
                kwargs["auth_token"] = os.environ["ANTHROPIC_AUTH_TOKEN"]
            self._client = anthropic.Anthropic(**kwargs)
        return self._client

    # ---------- request construction ----------
    def build_request(self, research: dict, *, fmt: str, scene_count: int, target_seconds: float, cinematic_allowed: int) -> dict:
        brief = {"format": fmt, "scene_count": scene_count, "target_duration_seconds": target_seconds,
                 "cinematic_scenes_allowed": cinematic_allowed, "aspect_ratio": "9:16"}
        data = security.neutralize(json.dumps(research, ensure_ascii=False), 16000)
        user = ("Direct this video. Brief (trusted, from the operator):\n" + json.dumps(brief) +
                f"\n\nReturn exactly {scene_count} scenes.\n<research>\n{data}\n</research>")
        return {
            "model": self.model,
            "max_tokens": self.settings.creative_director.max_output_tokens,
            "system": [{"type": "text", "text": prompts_v2.DIRECTOR, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": user}],
            "output_config": {"effort": self.settings.creative_director.effort,
                              "format": {"type": "json_schema", "schema": strict_json_schema(DirectorOutput)}},
        }

    def prompt_chars(self, request: dict) -> int:
        return len(prompts_v2.DIRECTOR) + sum(len(m["content"]) if isinstance(m["content"], str) else len(json.dumps(m["content"]))
                                              for m in request["messages"])

    # ---------- call ----------
    def call(self, request: dict) -> tuple[DirectorOutput, Usage, object]:
        import anthropic
        started = time.time()
        try:
            response = self.client().beta.messages.create(**request, betas=[FALLBACK_BETA], fallbacks="default")
        except anthropic.RateLimitError as exc:
            retry = exc.response.headers.get("retry-after") if getattr(exc, "response", None) is not None else None
            raise ProviderError(self.name, "rate_limit", str(exc)[:300], retry_after=float(retry) if retry else None) from exc
        except anthropic.AuthenticationError as exc:
            raise ProviderError(self.name, "auth", "Anthropic rejected the API key") from exc
        except anthropic.PermissionDeniedError as exc:
            raise ProviderError(self.name, "auth", str(exc)[:300]) from exc
        except anthropic.NotFoundError as exc:
            raise ProviderError(self.name, "bad_request", f"Model or endpoint not found ({self.model})") from exc
        except anthropic.BadRequestError as exc:
            raise ProviderError(self.name, "bad_request", str(exc)[:400]) from exc
        except anthropic.APITimeoutError as exc:
            raise ProviderError(self.name, "timeout", "Request timed out; it may still be billed") from exc
        except anthropic.APIConnectionError as exc:
            raise ProviderError(self.name, "unavailable", "Network error reaching the Anthropic API") from exc
        except anthropic.APIStatusError as exc:
            raise ProviderError(self.name, "server" if exc.status_code >= 500 else "bad_request", str(exc)[:300]) from exc
        u = response.usage
        served = getattr(response, "model", self.model) or self.model
        from ..orchestration.cost_controller import claude_cost
        usage = Usage(provider=self.name, model=served, input_tokens=u.input_tokens or 0, output_tokens=u.output_tokens or 0,
                      cache_read_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
                      cache_write_tokens=getattr(u, "cache_creation_input_tokens", 0) or 0,
                      request_id=getattr(response, "_request_id", None) or getattr(response, "id", None), seconds=round(time.time() - started, 2))
        cost = claude_cost(served, usage.input_tokens, usage.output_tokens, usage.cache_read_tokens, usage.cache_write_tokens)
        usage.cost_usd, usage.estimated = (cost if cost is not None else 0.0), cost is None
        if response.stop_reason == "refusal":
            raise ProviderError(self.name, "refused", f"Model declined: {getattr(response, 'stop_details', None)}")
        if response.stop_reason == "max_tokens":
            raise ProviderError(self.name, "invalid_output", "Output truncated at max_tokens")
        text = next((b.text for b in response.content if getattr(b, "type", "") == "text"), "")
        try:
            return DirectorOutput.model_validate_json(text), usage, response
        except Exception as exc:
            err = ProviderError(self.name, "invalid_output", f"Storyboard JSON failed validation: {str(exc)[:300]}")
            err.usage = usage  # type: ignore[attr-defined]
            raise err from exc

    def direct(self, research: dict, *, topic: dict, sources: list[Source], fmt: str, scene_count: int, target_seconds: float,
               cinematic_allowed: int, video_id: str, gate=None) -> tuple[Storyboard, list[Usage]]:
        """Generate + validate a storyboard. `gate(request)` is called before every API call (budget/approval) and
        must return a callback taking the resulting Usage (or None if the call failed before billing)."""
        request = self.build_request(research, fmt=fmt, scene_count=scene_count, target_seconds=target_seconds,
                                     cinematic_allowed=cinematic_allowed)
        research_text = json.dumps(research, ensure_ascii=False)
        usages: list[Usage] = []
        problems: list[str] = []
        for attempt in range(self.settings.creative_director.max_revisions + 1):
            settle = gate(request) if gate else (lambda usage: None)
            try:
                output, usage, response = self.call(request)
            except ProviderError as exc:
                settle(getattr(exc, "usage", None) if exc.kind != "timeout" else "unknown")
                if exc.kind != "invalid_output" or attempt == self.settings.creative_director.max_revisions:
                    raise
                problems = [exc.message]
                request = self._revise(request, None, problems)
                continue
            settle(usage)
            usages.append(usage)
            try:
                board = from_director(output, topic=topic, sources=sources, fmt=fmt, target=target_seconds, video_id=video_id,
                                      director={"provider": self.name, "model": usage.model, "requested_model": self.model,
                                                "attempts": attempt + 1, "created_at": time.time(), "interactive": False})
                problems = grounding_problems(board, research_text, cinematic_allowed)
            except ValueError as exc:
                problems = [str(exc)[:600]]
            if not problems:
                return board, usages
            if attempt == self.settings.creative_director.max_revisions:
                raise ProviderError(self.name, "invalid_output", "; ".join(problems)[:800])
            request = self._revise(request, response, problems)
        raise ProviderError(self.name, "invalid_output", "; ".join(problems)[:800])

    @staticmethod
    def _revise(request: dict, response, problems: list[str]) -> dict:
        """Append-only revision turn (keeps the cached prefix and any thinking blocks intact)."""
        messages = list(request["messages"])
        if response is not None:
            messages.append({"role": "assistant", "content": response.content})
        else:
            messages.append({"role": "assistant", "content": "{}"})
        messages.append({"role": "user", "content": "Fix these problems and return the full corrected JSON:\n- " + "\n- ".join(problems)})
        return {**request, "messages": messages}
