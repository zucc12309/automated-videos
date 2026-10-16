"""Cinematic footage providers.

HiggsfieldProvider uses the official `higgsfield-client` Python SDK (documented interface: submit(application, arguments)
-> request id; status(); result(); cancel(); credentials HF_KEY or HF_API_KEY + HF_API_SECRET). It is optional: nothing
in LOCAL or CLAUDE mode imports it, and every failure falls back to an approved Remotion scene.

Known SDK limits that shape this adapter:
* no cost-estimate endpoint  -> cost comes from cinematic.usd_per_second_upper_bound (user-verified) or explicit approval
* no idempotency key / lookup by client key -> a submit whose outcome is unknown is never retried automatically
* the 'application' endpoint id is account/model specific -> must be configured; it is never guessed

MockCinematicProvider renders a local FFmpeg clip; it exists for tests and dry runs and is labelled as mock everywhere.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

from .base import CinematicRequest, CostEstimate, ProviderError

CATALOG = Path(__file__).resolve().parents[1] / "data" / "higgsfield_catalog.json"
STATUS = {"queued": "queued", "in_progress": "in_progress", "completed": "completed", "failed": "failed", "nsfw": "nsfw",
          "canceled": "canceled", "cancelled": "canceled"}


def catalog() -> dict:
    return json.loads(CATALOG.read_text())


def _find_video_url(result) -> str | None:
    """Provider result shapes differ per application; find the first https URL that looks like a video."""
    stack = [result]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            for key in ("video", "videos", "url", "output", "outputs", "result", "results", "media"):
                if key in node:
                    stack.append(node[key])
            stack.extend(v for k, v in node.items() if k not in ("video", "videos", "url", "output", "outputs", "result", "results", "media"))
        elif isinstance(node, list):
            stack.extend(node)
        elif isinstance(node, str) and node.startswith("https://") and any(ext in node.lower() for ext in (".mp4", ".mov", ".webm", "video")):
            return node
    return None


class HiggsfieldProvider:
    name = "higgsfield"

    def __init__(self, settings, sdk=None):
        self.settings = settings
        self._sdk = sdk

    def sdk(self):
        if self._sdk is None:
            try:
                import higgsfield_client
            except ImportError as exc:
                raise ProviderError(self.name, "unavailable", "pip install higgsfield-client to enable Higgsfield") from exc
            self._sdk = higgsfield_client
        return self._sdk

    def available(self) -> tuple[bool, str]:
        c = self.settings.cinematic
        if not c.enabled:
            return False, "cinematic.enabled is false"
        if not c.application:
            return False, "cinematic.application (Higgsfield endpoint id from your Higgsfield API dashboard/docs) is not configured"
        if self._sdk is None:
            try:
                import higgsfield_client  # noqa: F401
            except ImportError:
                return False, "higgsfield-client is not installed"
        if not (os.environ.get("HF_KEY") or (os.environ.get("HF_API_KEY") and os.environ.get("HF_API_SECRET"))) and self._sdk is None:
            return False, "HF_KEY (or HF_API_KEY + HF_API_SECRET) is not set"
        return True, "configured"

    def capabilities(self) -> dict:
        snap = catalog()
        model = next((m for m in snap["models"] if m["id"] == self.settings.cinematic.model_label), None)
        return {"provider": self.name, "application": self.settings.cinematic.application, "model": model,
                "catalog_retrieved_at": snap["retrieved_at"], "cost_estimate_endpoint": False, "idempotency": False,
                "polling": True, "webhooks": True, "reference_images": bool(model and model.get("media_roles"))}

    def validate(self, request: CinematicRequest) -> None:
        model = self.capabilities()["model"]
        if not model:
            return   # unknown model: the provider will validate server-side; we still cap duration by budget
        if model.get("aspect_ratios") and request.aspect_ratio not in model["aspect_ratios"]:
            raise ProviderError(self.name, "bad_request", f"{model['id']} does not support {request.aspect_ratio}")
        if "duration_range" in model:
            lo, hi = model["duration_range"]
            if not lo <= request.duration_seconds <= hi:
                raise ProviderError(self.name, "bad_request", f"duration {request.duration_seconds}s outside {lo}-{hi}s")
        if "durations" in model and int(request.duration_seconds) not in model["durations"]:
            raise ProviderError(self.name, "bad_request", f"duration must be one of {model['durations']}")
        if request.resolution and model.get("resolutions") and request.resolution not in model["resolutions"]:
            raise ProviderError(self.name, "bad_request", f"resolution {request.resolution} not supported")

    def estimate_cost(self, request: CinematicRequest) -> CostEstimate:
        rate = self.settings.cinematic.usd_per_second_upper_bound
        if rate is None:
            return CostEstimate(usd=None, basis="Higgsfield SDK has no cost-estimate endpoint and no verified per-second price is configured")
        return CostEstimate(usd=round(rate * request.duration_seconds, 4), basis=f"configured upper bound ${rate}/s x {request.duration_seconds}s")

    def arguments(self, request: CinematicRequest) -> dict:
        """Translate the neutral spec into model parameters; only parameters the model is known to accept are sent."""
        model = self.capabilities()["model"]
        params = set(model.get("params", [])) if model else {"duration", "resolution"}
        args = {"prompt": request.prompt + (". Avoid: " + ", ".join(request.negative_guidance) if request.negative_guidance else ""),
                "aspect_ratio": request.aspect_ratio}
        if "duration" in params or (model and ("duration_range" in model or "durations" in model)):
            args["duration"] = int(round(request.duration_seconds))
        if "resolution" in params:
            args["resolution"] = request.resolution
        if "generate_audio" in params:
            args["generate_audio"] = False      # narration and SFX come from the local mix
        if "sound" in params:
            args["sound"] = "off"
        if request.seed is not None:
            args["seed"] = request.seed
        if request.reference_images:
            args["input_images"] = request.reference_images[:2]
        args.update(request.params)
        return args

    def submit(self, request: CinematicRequest, idempotency_key: str) -> str:
        self.validate(request)
        try:
            controller = self.sdk().submit(self.settings.cinematic.application, arguments=self.arguments(request))
        except ProviderError:
            raise
        except Exception as exc:
            text = str(exc)
            kind = "auth" if "401" in text or "403" in text or "credential" in text.lower() else \
                "budget" if "402" in text or "credit" in text.lower() else \
                "rate_limit" if "429" in text else "bad_request" if "400" in text or "422" in text else "unknown_outcome"
            raise ProviderError(self.name, kind, text[:300]) from exc
        return controller.request_id

    def get_status(self, remote_id: str) -> str:
        status = self.sdk().status(remote_id)
        return STATUS.get(type(status).__name__.lower().replace("inprogress", "in_progress"), "in_progress")

    def fetch_result(self, remote_id: str) -> dict:
        raw = self.sdk().result(remote_id)
        url = _find_video_url(raw)
        if not url:
            raise ProviderError(self.name, "invalid_output", "No video URL in provider result")
        return {"video_url": url, "raw": raw}


class MockCinematicProvider:
    """Deterministic local stand-in. Produces a real H.264 clip (graded gradient + slow push) via FFmpeg, no network."""
    name = "mock"

    def __init__(self, settings, out_dir: Path, fail: str = ""):
        self.settings, self.out_dir, self.fail = settings, out_dir, fail
        self.jobs: dict[str, dict] = {}

    def available(self) -> tuple[bool, str]:
        return True, "mock provider (no real footage)"

    def capabilities(self) -> dict:
        return {"provider": self.name, "model": {"id": "mock-cinematic-v1", "aspect_ratios": ["9:16", "16:9", "1:1"], "duration_range": [1, 15]},
                "cost_estimate_endpoint": True, "idempotency": True, "polling": True}

    def validate(self, request: CinematicRequest) -> None:
        if not 1 <= request.duration_seconds <= 15:
            raise ProviderError(self.name, "bad_request", "duration outside 1-15s")

    def estimate_cost(self, request: CinematicRequest) -> CostEstimate:
        rate = self.settings.cinematic.usd_per_second_upper_bound
        return CostEstimate(usd=round((rate if rate is not None else 0.1) * request.duration_seconds, 4), basis="mock rate", upper_bound=True)

    def submit(self, request: CinematicRequest, idempotency_key: str) -> str:
        if self.fail == "submit_timeout":
            raise ProviderError(self.name, "unknown_outcome", "submit timed out")
        if self.fail == "unavailable":
            raise ProviderError(self.name, "unavailable", "mock outage")
        remote = "mock_" + idempotency_key[:16]
        self.jobs[remote] = {"request": request, "at": time.time()}
        return remote

    def get_status(self, remote_id: str) -> str:
        return "failed" if self.fail == "generation" else "completed"

    def fetch_result(self, remote_id: str) -> dict:
        request = self.jobs[remote_id]["request"]
        self.out_dir.mkdir(parents=True, exist_ok=True)
        out = self.out_dir / f"{remote_id}.mp4"
        if self.fail == "corrupt":
            out.write_bytes(b"not a video")
            return {"video_path": str(out), "raw": {"mock": True}}
        w, h = (720, 1280) if request.aspect_ratio == "9:16" else (1280, 720)
        seconds = max(1.0, request.duration_seconds)
        hue = sum(map(ord, request.prompt)) % 360
        vf = (f"geq=r='40+30*sin(2*PI*(X/{w}+T/7))':g='45+25*sin(2*PI*(Y/{h}+T/9))':b='70+50*sin(2*PI*((X+Y)/{w+h}+T/5))',"
              f"hue=h={hue}:s=0.6,noise=alls=6:allf=t,vignette=PI/4,"
              f"zoompan=z='min(1+0.0015*on,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={w}x{h}:fps=30")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:r=30:d={seconds}",
                        "-vf", vf, "-t", str(seconds), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", str(out)],
                       check=True, timeout=300)
        return {"video_path": str(out), "raw": {"mock": True}}
