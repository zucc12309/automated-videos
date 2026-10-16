"""V2 production pipeline: research -> direction -> storyboard -> cost/approval -> assets -> narration -> render -> QA -> repair.

Every stage checkpoints to the job folder, so a restarted worker resumes instead of redoing (and re-paying for) work.
V1 contracts are kept: plan.json, props.json, checks.json, provenance.json, status.json, video.mp4, poster.jpg.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np

from .. import audio as audio_fx, security, settings as settings_mod, tts, variety
from ..creative import director, semantic_router
from ..providers.base import CinematicRequest, ProviderError
from ..providers.claude_provider import ClaudeProvider
from ..schemas.storyboard import Storyboard, from_plan, to_plan_dict
from . import job_state
from .asset_manager import AssetManager, file_hash, probe_video, cache_key
from .cost_controller import (ApprovalRequired, BudgetExceeded, CostController, PaidGenerationDisabled, claude_upper_bound)

RATE = 24000


class Paused(RuntimeError):
    """Raised to stop the worker cleanly while a paid request waits for approval."""


def _save(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(security.redact(value), ensure_ascii=False, indent=2))
    tmp.replace(path)


def _load(path: Path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


class Pipeline:
    def __init__(self, job_id: str, *, root: Path, data: Path, cfg: settings_mod.Settings, claude_client=None, cinematic_provider=None):
        self.job_id, self.root, self.data, self.cfg = job_id, root, data, cfg
        self.folder = data / "jobs" / job_id
        self.public = root / "public" / "jobs" / job_id
        self.costs = CostController(data, cfg)
        self.assets = AssetManager(data)
        self.claude = ClaudeProvider(cfg, client=claude_client)
        self._cinematic = cinematic_provider
        self.timings: dict[str, float] = _load(self.folder / "timings.json", {}) or {}
        self.decisions: list[dict] = _load(self.folder / "decisions.json", []) or []

    # ---------- helpers ----------
    def phase(self, phase: str, stage: str | None = None, **fields):
        if job_state.cancel_requested(self.folder):
            raise job_state.Canceled("Canceled by user")
        job_state.transition(self.folder, phase, stage=stage or phase.lower(), **fields)

    def timed(self, name: str, started: float):
        self.timings[name] = round(self.timings.get(name, 0) + time.time() - started, 2)
        _save(self.folder / "timings.json", self.timings)

    def decide(self, **entry):
        self.decisions.append({**entry, "at": time.time()})
        _save(self.folder / "decisions.json", self.decisions)

    def cinematic_provider(self):
        if self._cinematic is None:
            if self.cfg.cinematic.provider == "higgsfield_mcp":
                from .footage import HiggsfieldMCPProvider
                self._cinematic = HiggsfieldMCPProvider(self.cfg)
            elif self.cfg.cinematic.provider == "mock":
                from ..providers.higgsfield_provider import MockCinematicProvider
                self._cinematic = MockCinematicProvider(self.cfg, self.data / "mock_cinematic")
            else:
                from ..providers.higgsfield_provider import HiggsfieldProvider
                self._cinematic = HiggsfieldProvider(self.cfg)
        return self._cinematic

    # ---------- stage: direction ----------
    def claude_gate(self, request: dict):
        """Budget gate for one Claude call: reserve the upper bound, then reconcile with real usage."""
        cap = self.cfg.budget.max_claude_calls_per_video
        if self.costs.calls_for_job(self.job_id, "claude") >= cap:
            raise BudgetExceeded(f"max_claude_calls_per_video ({cap}) reached")
        estimate = claude_upper_bound(self.claude.model, self.claude.prompt_chars(request), request["max_tokens"])
        key = hashlib.sha256(json.dumps(request["messages"], default=str).encode()).hexdigest()
        reservation = self.costs.authorize(self.folder, provider="claude", kind="creative_direction", estimate_usd=estimate,
                                           request_key=key, note=f"{self.claude.model} upper bound")

        def settle(usage):
            if usage is None:
                self.costs.release(reservation["id"], "request rejected before billing")
            elif usage == "unknown":
                self.costs.commit(reservation["id"], None)      # timeout: keep the conservative reserved amount
            else:
                self.costs.commit(reservation["id"], None if usage.estimated else usage.cost_usd,
                                  usage={"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens,
                                         "cache_read_tokens": usage.cache_read_tokens, "cache_write_tokens": usage.cache_write_tokens,
                                         "model": usage.model, "request_id": usage.request_id})
        return settle

    def preflight_claude(self, mode: str) -> str:
        """Decide before calling Claude whether it may be called; returns the effective mode."""
        if mode == "local":
            return mode
        ok, why = self.claude.available()
        if not ok:
            self.decide(stage="direction", provider="claude", used=False, reason=why, fallback="local")
            return "local"
        b = self.cfg.budget
        if not b.allow_paid_generation or b.approval_policy == "deny":
            self.decide(stage="direction", provider="claude", used=False, fallback="local",
                        reason="paid generation disabled (budget.allow_paid_generation=false or approval_policy=deny)")
            return "local"
        if b.approval_policy == "explicit":
            ap = self.costs.approvals(self.folder)
            if float(ap.get("job_cap_usd") or 0) <= 0:
                request = {"request_id": "req_claude_direction", "job_id": self.job_id, "provider": "claude", "kind": "creative_direction",
                           "estimate_usd": claude_upper_bound(self.claude.model, 30000, self.cfg.creative_director.max_output_tokens),
                           "estimate_known": True, "note": "upper bound for one Claude storyboard call", "at": time.time()}
                if b.on_missing_approval == "pause":
                    ap["pending"][request["request_id"]] = request
                    self.costs.save_approvals(self.folder, ap)
                    raise Paused("Claude direction needs approval: call approve_generation with this job id and a USD cap")
                self.decide(stage="direction", provider="claude", used=False, fallback="local",
                            reason="explicit approval policy and no approved budget for this job")
                return "local"
        return mode

    def direct(self, request: dict) -> Storyboard:
        path = self.folder / "storyboard.json"
        if path.exists():
            return Storyboard.model_validate_json(path.read_text())
        started = time.time()
        mode = request.get("mode", "local")
        seed = request.get("seed") or self.job_id
        if request.get("storyboard"):
            board = Storyboard.model_validate(request["storyboard"])
            board.video_id, board.seed = self.job_id, board.seed or seed
            board.director = {**board.director, "supplied": True}
            # Supplied storyboards keep their authored hook (candidates are scored and recorded) but get the contextual CTA.
            board = director.finish(board, request.get("topic"), self.cfg, choose_hook=False)
            self.decide(stage="direction", provider=board.director.get("provider", "supplied"), used=True, note="storyboard supplied by caller")
            topic = request.get("topic") or _load(self.folder / "topic.json")
            if topic:
                from ..creative import research
                report = research.verify(board, topic)     # supplied copy is checked against the supplied sources too
                board = Storyboard.model_validate(board.model_dump())
            else:
                report = {"note": "supplied storyboard; claims not re-verified (no topic data)"}
        elif request.get("plan"):
            board = from_plan(request["plan"], video_id=self.job_id)
            board.seed = seed
            board = director.local_direction(board, self.cfg, seed, mode == "hybrid" and self.cfg.cinematic.enabled)
            self.decide(stage="direction", provider="local", used=True, note="V1 plan supplied; local heuristic direction")
            report = {"note": "supplied plan; no topic data to verify against"}
        else:
            self.phase("RESEARCHING", "researching_sources")
            topic = _load(self.folder / "topic.json")
            self.phase("SCRIPTING", "writing_english_script")
            effective = self.preflight_claude(mode)
            self.phase("DIRECTING", "creative_direction")
            board, report, usages = director.create_storyboard(
                topic, self.cfg, mode=effective, video_id=self.job_id, seed=seed,
                claude=self.claude if effective != "local" else None, gate=self.claude_gate, decisions=self.decisions,
                cinematic=mode == "hybrid" and self.cfg.cinematic.enabled)
            _save(self.folder / "decisions.json", self.decisions)
            if usages:
                _save(self.folder / "claude_usage.json", [u.__dict__ for u in usages])
        _save(self.folder / "verification.json", report)
        _save(path, board.model_dump())
        _save(self.folder / "script.json", to_plan_dict(board))
        job_state.checkpoint(self.folder, "direction", storyboard=str(path))
        self.timed("creative_direction", started)
        return board

    # ---------- stage: estimate ----------
    def estimate(self, board: Storyboard, mode: str) -> dict:
        provider_rows = []
        if mode == "hybrid" and self.cfg.cinematic.enabled:
            provider = self.cinematic_provider()
            for scene in self.cinematic_scenes(board):
                req = self.cinematic_request(scene)
                est = provider.estimate_cost(req)
                cached = self.assets.lookup(self.cache_key_for(req, provider)) is not None
                provider_rows.append({"scene": scene.id, "provider": provider.name, "seconds": req.duration_seconds,
                                      "usd": 0.0 if cached else est.usd, "cached": cached, "basis": est.basis})
        unknown = any(r["usd"] is None for r in provider_rows)
        claude_rows = _load(self.folder / "claude_usage.json", []) or []
        estimate = {"job_id": self.job_id, "mode": mode,
                    "claude_actual_usd": round(sum(u.get("cost_usd", 0) for u in claude_rows), 6),
                    "cinematic": provider_rows,
                    "cinematic_usd": None if unknown else round(sum(r["usd"] or 0 for r in provider_rows), 4),
                    "uncertainty": "unknown: provider has no cost estimate; explicit approval with a USD cap required" if unknown else
                                   "upper bound from configured rates" if provider_rows else "no paid generation planned",
                    "local_only": mode == "local" or not provider_rows}
        _save(self.folder / "estimate.json", estimate)
        return estimate

    # ---------- stage: cinematic assets ----------
    def cinematic_scenes(self, board: Storyboard):
        from . import footage
        return footage.selected_scenes(board, self.cfg)

    def cinematic_request(self, scene) -> CinematicRequest:
        from . import footage
        return footage.request_for(scene, on_unsafe=lambda url: self.decide(stage="cinematic", scene=scene.id, dropped_reference=url[:120],
                                                                             reason="unsafe URL"))

    def cache_key_for(self, req: CinematicRequest, provider) -> str:
        from . import footage
        return footage.key_for(req, provider, self.cfg)

    def fallback_scene(self, board: Storyboard, scene, reason: str):
        scene.render_engine = "remotion"
        scene.layout = scene.cinematic.fallback_layout if scene.cinematic else scene.fallback_layout
        scene.qa.status = "fallback"
        scene.qa.issues.append(f"cinematic fallback: {reason}"[:200])
        self.decide(stage="cinematic", scene=scene.id, used=False, reason=reason, fallback=f"remotion:{scene.layout}")

    def generate_assets(self, board: Storyboard, mode: str) -> Storyboard:
        if mode != "hybrid":
            for s in board.scenes:
                if s.render_engine == "cinematic":
                    self.fallback_scene(board, s, f"{mode} mode renders everything in Remotion")
            return board
        if not self.cfg.cinematic.enabled:
            for s in board.scenes:
                if s.render_engine == "cinematic":
                    self.fallback_scene(board, s, "cinematic.enabled is false")
            return board
        provider = self.cinematic_provider()
        ok, why = provider.available()
        wanted = self.cinematic_scenes(board)
        for s in board.scenes:
            if s.render_engine == "cinematic" and s not in wanted:
                self.fallback_scene(board, s, "over max cinematic scenes/duration")
        if not wanted:
            return board
        if not ok:
            for s in wanted:
                self.fallback_scene(board, s, f"provider unavailable: {why}")
            return board
        self.phase("GENERATING_ASSETS", "generating_cinematic_assets")
        started = time.time()
        journal_path = self.folder / "generation_journal.json"
        journal = _load(journal_path, {}) or {}
        for scene in wanted:
            req = self.cinematic_request(scene)
            key = self.cache_key_for(req, provider)
            target = self.public / "cinematic" / f"{scene.id}.mp4"
            hit = self.assets.lookup(key) if self.cfg.cinematic.cache_assets else None
            if hit:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(hit["path"], target)
                self.attach(scene, target, hit, cached=True)
                continue
            if getattr(provider, "brokered", False):
                # Higgsfield via MCP: the agent attaches footage before rendering; nothing to submit from here.
                self.fallback_scene(board, scene, "no Higgsfield footage attached for this shot (plan_footage → attach_footage)")
                continue
            entry = journal.get(scene.id, {})
            if entry.get("state") == "submitting":
                # Previous worker died between submit and recording the remote id: outcome unknown, never resubmit blindly.
                self.fallback_scene(board, scene, "previous submit outcome unknown (no idempotency in provider); reconcile manually before retrying")
                entry["state"] = "unknown_outcome"
                journal[scene.id] = entry
                _save(journal_path, journal)
                continue
            if entry.get("state") == "unknown_outcome":
                self.fallback_scene(board, scene, "unresolved unknown-outcome submission")
                continue
            try:
                provider.validate(req)
                est = provider.estimate_cost(req)
                reservation = entry.get("reservation") or self.costs.authorize(
                    self.folder, provider=provider.name, kind="cinematic", estimate_usd=est.usd, request_key=key,
                    note=f"{scene.id} {req.duration_seconds}s; {est.basis}")
            except ApprovalRequired as exc:
                if self.cfg.budget.on_missing_approval == "pause":
                    _save(self.folder / "storyboard.json", board.model_dump())
                    raise Paused(f"Cinematic scene {scene.id} needs approval ({exc.request['request_id']})") from exc
                self.fallback_scene(board, scene, f"approval required ({exc.request['request_id']}); policy=fallback")
                continue
            except (BudgetExceeded, PaidGenerationDisabled) as exc:
                self.fallback_scene(board, scene, str(exc))
                continue
            except ProviderError as exc:
                self.fallback_scene(board, scene, exc.message)
                continue
            remote = entry.get("remote_id")
            if not remote:
                journal[scene.id] = {"state": "submitting", "reservation": reservation, "key": key, "at": time.time()}
                _save(journal_path, journal)
                try:
                    remote = provider.submit(req, idempotency_key=key)
                except ProviderError as exc:
                    if exc.kind == "unknown_outcome":
                        journal[scene.id]["state"] = "unknown_outcome"
                        _save(journal_path, journal)
                        self.costs.commit(reservation["id"], None)       # may have been charged: keep the reservation
                        self.fallback_scene(board, scene, "submit outcome unknown; reserved cost kept, not resubmitted")
                    else:
                        self.costs.release(reservation["id"], exc.message)
                        journal.pop(scene.id, None)
                        _save(journal_path, journal)
                        self.fallback_scene(board, scene, exc.message)
                    continue
                journal[scene.id] = {"state": "submitted", "remote_id": remote, "reservation": reservation, "key": key, "at": time.time()}
                _save(journal_path, journal)
            try:
                path = self.await_result(provider, remote, target)
                meta = probe_video(path)
            except (ProviderError, ValueError, TimeoutError) as exc:
                journal[scene.id]["state"] = "failed"
                _save(journal_path, journal)
                self.costs.commit(reservation["id"], None)    # generation ran; assume charged at the reserved bound
                self.fallback_scene(board, scene, f"generation failed: {getattr(exc, 'message', str(exc))[:160]}")
                continue
            self.costs.commit(reservation["id"], est.usd)
            stored = self.assets.store(key, path, {"provider": provider.name, "remote_id": remote, "prompt": req.prompt,
                                                   "duration": req.duration_seconds, "model": provider.capabilities().get("model"),
                                                   "generated_at": time.time(), "probe": meta, "mock": provider.name == "mock"})
            journal[scene.id]["state"] = "done"
            _save(journal_path, journal)
            self.attach(scene, path, stored, cached=False)
        self.timed("cinematic_generation_wait", started)
        return board

    def attach_motion_clips(self, board: Storyboard) -> Storyboard:
        """Resolve `library:<id>` graphic assets into job-local files Remotion can play."""
        from .motion_library import MotionLibrary
        library = MotionLibrary(self.data)
        for scene in board.scenes:
            for asset in scene.assets:
                if asset.kind != "graphic" or not asset.path.startswith("library:"):
                    continue
                try:
                    clip = library.get(asset.path.split(":", 1)[1])
                except KeyError as exc:
                    scene.qa.issues.append(str(exc)[:200])
                    scene.assets = [a for a in scene.assets if a is not asset]
                    self.decide(stage="motion_clip", scene=scene.id, used=False, reason=str(exc))
                    continue
                target = self.public / "motion" / f"{scene.id}{Path(clip['file']).suffix}"
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(clip["path"], target)
                asset.path = str(target.relative_to(self.root / "public"))
                asset.sha256 = asset.sha256 or clip["id"]
                asset.provider = clip.get("origin", "imported")
                asset.provenance = {"library_id": clip["id"], "title": clip.get("title"), "duration": clip["probe"]["duration"],
                                    "origin": clip.get("origin"), "imported_at": clip.get("imported_at")}
                scene.layout = "motionClip"
                self.decide(stage="motion_clip", scene=scene.id, used=True, library_id=clip["id"], origin=clip.get("origin"))
        return board

    def await_result(self, provider, remote: str, target: Path) -> Path:
        deadline = time.time() + self.cfg.cinematic.timeout_seconds
        while True:
            status = provider.get_status(remote)
            if status == "completed":
                break
            if status in ("failed", "nsfw", "canceled"):
                raise ProviderError(provider.name, "invalid_output", f"generation {status}")
            if time.time() > deadline:
                raise TimeoutError("cinematic generation timed out; it may still finish remotely")
            if job_state.cancel_requested(self.folder):
                raise job_state.Canceled("Canceled by user")
            time.sleep(self.cfg.cinematic.poll_interval_seconds)
        result = provider.fetch_result(remote)
        target.parent.mkdir(parents=True, exist_ok=True)
        if result.get("video_path"):
            shutil.copyfile(result["video_path"], target)
        else:
            AssetManager.download(result["video_url"], target, self.cfg.cinematic.max_download_mb)
        return target

    def attach(self, scene, path: Path, record: dict, cached: bool):
        from ..schemas.storyboard import Asset
        rel = str(path.relative_to(self.root / "public"))
        scene.assets = [a for a in scene.assets if a.kind != "cinematic"] + [
            Asset(kind="cinematic", path=rel, sha256=record.get("sha256", ""), provider=record.get("provider", ""),
                  provenance={"cache_key": record.get("key"), "remote_id": record.get("remote_id"), "cached": cached,
                              "duration": (record.get("probe") or {}).get("duration") or probe_video(path)["duration"],
                              "mock": record.get("mock", False), "generated_at": record.get("generated_at")})]
        scene.layout = "hookBold" if scene.role == "hook" else "cinematic"     # hooks keep bold type over the footage
        self.decide(stage="cinematic", scene=scene.id, used=True, cached=cached, provider=record.get("provider"), mock=record.get("mock", False))

    # ---------- reference audio profile ----------
    def _profile(self) -> dict | None:
        if self.cfg.narration.audio_profile != "reference":
            return None
        if not hasattr(self, "_profile_cache"):
            from .. import audio_profile
            self._profile_cache = audio_profile.profile() if audio_profile.PROFILE.exists() else None
        return self._profile_cache

    def _audio_profile_key(self) -> str:
        p = self._profile()
        return hashlib.sha256(json.dumps(p, sort_keys=True).encode()).hexdigest()[:12] if p else "off"

    # ---------- stage: narration ----------
    def narrate(self, board: Storyboard, fps: int) -> list[dict]:
        self.phase("SYNTHESIZING_AUDIO", "loading_local_voice")
        started = time.time()
        if any(d.get("provider") == "ollama" and d.get("used") for d in self.decisions):
            from .. import engine as _engine, resources
            self.decide(stage="resources", action="unload_ollama", ok=resources.release_ollama(_engine.OLLAMA, self.cfg.model))
        engine, why = tts.available_engine(self.cfg.narration.engine)
        self.decide(stage="narration", engine=engine, reason=why)
        self.public.mkdir(parents=True, exist_ok=True)
        out = []
        for i, scene in enumerate(board.scenes):
            key = hashlib.sha256(json.dumps([scene.narration, engine, self.cfg.voice, self.cfg.voice_speed,
                                             self.cfg.narration.pronunciations, self._audio_profile_key()], sort_keys=True).encode()).hexdigest()[:16]
            meta_path = self.public / f"scene-{i}.json"
            wav = self.public / f"scene-{i}.wav"
            cached = _load(meta_path)
            if cached and cached.get("key") == key and wav.exists():
                out.append(cached)
                continue
            job_state.transition(self.folder, "SYNTHESIZING_AUDIO", stage=f"narrating_scene_{i + 1}_of_{len(board.scenes)}")
            n = tts.narrate(scene.narration, self.cfg, fps, engine)
            import soundfile as sf
            raw = self.public / f"scene-{i}-raw.wav"
            sf.write(raw, n.audio, RATE)
            eq, eq_info = "", None
            if self._profile():          # move the voice's tonal balance toward Reference A (clamped ±6 dB per band)
                from .. import audio_profile
                strength = self._profile()["targets"]["narration_eq"].get("kokoro_strength", .5) if n.engine.startswith("kokoro") else 1.0
                eq, eq_info = audio_profile.match_eq(n.audio, RATE, self._profile()["measured"]["voice_bands_db"], strength)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af",
                            "highpass=f=75," + (eq + "," if eq else "") +
                            "acompressor=threshold=-20dB:ratio=2.5:attack=5:release=80,loudnorm=I=-16:TP=-1.5:LRA=7",
                            "-ar", str(RATE), "-ac", "1", str(wav)], check=True, timeout=300)
            raw.unlink()
            normalized, _ = sf.read(wav, dtype="float32")
            from .. import alignment
            record = {"key": key, "engine": n.engine, "voice": n.voice, "timing_source": n.timing_source, "notes": n.notes, "eq": eq_info,
                      "seconds": len(n.audio) / RATE, "words": n.words, "visemes": n.visemes,
                      "mouth": audio_fx.mouth_envelope(normalized, fps), "sync": alignment.sync_error(n.words, normalized, RATE)}
            _save(meta_path, record)
            out.append(record)
        self.phase("ALIGNING", "aligning_captions")
        job_state.checkpoint(self.folder, "narration", engine=engine, scenes=len(out))
        self.timed("narration", started)
        return out

    # ---------- stage: props + render ----------
    def build_props(self, board: Storyboard, narration: list[dict], *, variant_seed: str | None = None, overrides: dict | None = None) -> dict:
        cfg, fps = self.cfg, self.cfg.frame_rate
        width, height = cfg.size
        overrides = overrides or {}
        theme = overrides.get("theme") or board.creative_direction.theme
        character_mode = board.creative_direction.character if board.creative_direction.character != "auto" else cfg.production.character
        any_character = character_mode == "on" or (character_mode == "auto" and any(s.character for s in board.scenes))
        seed = (variant_seed or board.seed or self.job_id) + (f":r{overrides['reseed']}" if overrides.get("reseed") else "")
        variant = variety.choose_variant(seed, self.data / "variety.json", theme=theme,
                                         character=any_character)
        if overrides.get("captions"):
            variant["captions"] = overrides["captions"]
        plan = to_plan_dict(board)
        scenes, cursor = [], 0
        roundup = board.format == "roundup"
        for i, (scene, story, voice) in enumerate(zip(plan["scenes"], board.scenes, narration)):
            seconds = voice["seconds"]
            tails = (self._profile() or {}).get("targets", {}).get("scene_tail_s") or {"default": .28, "demonstration": .55, "pause": .55}
            tail = tails.get(story.pace, tails["default"])
            length = math.ceil((seconds + tail) * fps)
            lo, hi = variety.PACE.get(story.pace, (1.3, 3.0))
            media = None if story.id in overrides.get("drop_media", []) else next((a.path for a in story.assets if a.kind == "cinematic"), None)
            media = media if media and self._safe_media(media) else None
            media_seconds = next((a.provenance.get("duration") for a in story.assets if a.kind == "cinematic"), None)
            motion = next((a for a in story.assets if a.kind == "graphic" and not a.path.startswith("library:")), None)
            if motion and self._safe_media(motion.path):
                media, media_seconds = motion.path, motion.provenance.get("duration")
            hint = overrides.get("layout_hints", {}).get(story.id) or story.layout
            if hint == "cinematic" and not media:
                hint = story.fallback_layout
            words = voice["words"]
            scenes.append({**scene, "audio": f"jobs/{self.job_id}/scene-{i}.wav", "frames": length,
                           "audioFrames": math.ceil(seconds * fps), "uiAudio": f"jobs/{self.job_id}/scene-{i}-ui.wav",
                           "words": words, "mouth": voice["mouth"], "visemes": voice["visemes"],
                           "beats": variety.split_beats(words, length / fps, lo, hi), "_roundup": roundup,
                           "transitionFrames": 0, "from": cursor,
                           # V2 additions
                           "id": story.id, "role": story.role, "intent": story.intent, "pace": story.pace,
                           "visualData": story.visual.model_dump(), "motion": story.motion.model_dump(), "media": media, "mediaSeconds": media_seconds,
                           "layoutHint": hint, "avoidLayouts": overrides.get("avoid", {}).get(story.id, []),
                           "cta": story.cta or None, "character_action": story.character_action,
                           "_stars": (board.repos[story.item - 1].get("stars", 0) if roundup and 0 < story.item <= len(board.repos) else 0),
                           "motionClip": bool(motion) and media == (motion.path if motion else None),
                           "character": False if story.id in overrides.get("hide_character", []) else
                                        (bool(story.character) if character_mode == "auto" else character_mode == "on"),
                           "claimIds": story.claim_ids})
            cursor += length
        duration = scenes[-1]["from"] + scenes[-1]["frames"]
        layouts = variety.plan_layouts(scenes, variant)
        style = "premium" if cfg.production.style == "premium" and (overrides.get("theme") or theme) in ("fieldnotes-premium", None, "") else "studio"
        direction = None
        if style == "premium":
            from ..creative import visual_director
            direction = visual_director.direct(scenes, character_mode="off" if character_mode == "off" else "on")
            layouts = [b["layout"] for s in scenes for b in s["beats"]]
        for s in scenes:
            s.pop("_roundup", None)
            s.pop("_repo", None)
            s.pop("_listItems", None)
            s.pop("_noLoop", None)
        readmes = {r.get("full_name"): re.sub(r"\s+", " ", r.get("readme_excerpt") or "")[:900] for r in board.repos}
        repos = [{**r, "readme": readmes.get(r.get("full_name"), "")} for r in plan["repos"]]
        for s in scenes:
            s.pop("_stars", None)
        return {"title": board.title, "style": style, "brand": cfg.brand_profile.wordmark or cfg.brand, "series": board.series,
                "direction": direction,
                "repos": repos, "music": None, "variant": variant, "scenes": scenes, "fps": fps, "width": width,
                "height": height, "durationInFrames": duration, "schemaVersion": "2.0", "theme": variant.get("theme"),
                "characterMode": character_mode, "_layouts": layouts}

    def master(self, video: Path, *, from_master: bool = False) -> dict:
        """-14 LUFS / <= -1 dBTP. AAC encoding can overshoot the limiter, so the encoded true peak is measured and corrected."""
        from ..quality.audio_analysis import loudness
        out = self.folder / "video-master.mp4"
        chain = "volume=0dB" if from_master else "loudnorm=I=-14:TP=-1.5:LRA=9,alimiter=limit=0.8:attack=1:release=50:level=false"
        if not from_master and self._profile():
            # Linear gain to the target: single-pass loudnorm is dynamic and lifts every pause, which flattens the mix that
            # Reference A keeps (its quietest 5% sits ~28 dB under the voice peaks).
            target = self._profile()["targets"]["master"]["integrated_lufs"]
            current = loudness(video).get("integrated_lufs")
            if current is not None:
                chain = f"volume={target - current:.2f}dB,alimiter=limit=0.84:attack=1:release=60:level=false"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-c:v", "copy", "-af", chain, "-ar", "48000", "-c:a", "aac",
                        "-b:a", "192k", str(out)], check=True, timeout=600)
        measured = loudness(out)
        tp = measured.get("true_peak_dbtp")
        if tp is not None and tp > -1.0:
            fixed = self.folder / "video-master2.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out), "-c:v", "copy", "-af", f"volume={-1.2 - tp:.2f}dB", "-ar", "48000",
                            "-c:a", "aac", "-b:a", "192k", str(fixed)], check=True, timeout=600)
            fixed.replace(out)
            measured = loudness(out)
        out.replace(video)
        return measured

    def _safe_media(self, rel: str) -> bool:
        """Only real files inside public/ may reach Remotion's staticFile (supplied storyboards are untrusted)."""
        try:
            path = security.inside(self.root / "public", self.root / "public" / rel)
        except ValueError:
            return False
        return path.is_file()

    def render(self, props: dict) -> Path:
        self.phase("RENDERING", "rendering")
        started = time.time()
        fps = props["fps"]
        layouts = props.pop("_layouts")
        for i, scene in enumerate(props["scenes"]):
            audio_fx.beat_sfx(self.public / f"scene-{i}-ui.wav", scene["frames"] / fps, scene["beats"], scene["words"], scene.get("emphasis", ""))
        if self.cfg.music:
            speech = [(s["from"] / fps + w["s"], s["from"] / fps + w["e"]) for s in props["scenes"] for w in s["words"]]
            music = props["variant"]["music"]
            bed = (self._profile() or {}).get("targets", {}).get("music") or {}
            audio_fx.music_bed(self.public / "music-raw.wav", props["durationInFrames"] / fps, music["bpm"], music["progression"], speech,
                               style=bed.get("style", "lofi"), duck_db=bed.get("duck_db", -7.0))
            level = "loudnorm=I=-31:TP=-6"
            if self._profile():          # Reference A: bed sits a measured distance under the voice (pauses keep their dynamics)
                import soundfile as sf
                from .. import audio_profile
                voice = [sf.read(self.public / f"scene-{i}.wav", dtype="float32")[0] for i in range(len(props["scenes"]))]
                raw, _ = sf.read(self.public / "music-raw.wav", dtype="float32")
                gain = audio_profile.bed_gain_db(voice, raw, RATE, self._profile()["measured"]["bed_minus_speech_db"])
                level = f"volume={gain}dB"
                self.decide(stage="music", style=bed.get("style"), gain_db=gain, basis="reference bed level")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(self.public / "music-raw.wav"), "-af", level,
                            "-ar", str(RATE), str(self.public / "music.wav")], check=True, timeout=300)
            (self.public / "music-raw.wav").unlink()
            props["music"] = f"jobs/{self.job_id}/music.wav"
        _save(self.folder / "props.json", props)
        video = self.folder / "video.mp4"
        cli = self.root / "node_modules" / ".bin" / "remotion"
        from .. import resources
        free = resources.available_memory_gb()
        tabs = resources.render_concurrency(self.cfg.renderer.concurrency, free)
        self.decide(stage="render", concurrency=tabs, memory_available_gb=free)
        args = [str(cli), "render", "src/index.tsx", "Explainer", str(video), f"--props={self.folder / 'props.json'}", "--codec=h264",
                f"--concurrency={tabs}", "--log=error"]
        if self.cfg.browser():
            args.append(f"--browser-executable={self.cfg.browser()}")
        subprocess.run(args, cwd=self.root, check=True, timeout=self.cfg.renderer.timeout_seconds, env=security.child_env())
        self.master(video)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "0.5", "-i", str(video), "-frames:v", "1", str(self.folder / "poster.jpg")],
                       check=True, timeout=120)
        variety.remember(props["variant"], layouts, self.data / "variety.json")
        props["_layouts"] = layouts
        job_state.checkpoint(self.folder, "render", video=str(video))
        self.timed("render", started)
        return video

    # ---------- stage: QA + repair ----------
    def qa_and_repair(self, board: Storyboard, narration: list[dict], props: dict, video: Path) -> tuple[dict, dict]:
        from ..quality import quality_report
        qc = self.cfg.quality_control
        attempts = 0
        repairs_log = []
        while True:
            self.phase("VALIDATING", "quality_checks")
            started = time.time()
            report = quality_report.run(video, props, narration, board.model_dump(), self.folder / "qa")
            self.timed("qa", started)
            summary = report["summary"]
            needs = (not summary["technical_pass"]) or bool(report["visual"]["issues"])
            if not qc.enabled or not needs or attempts >= qc.max_repairs:
                break
            overrides = quality_report.plan_repairs(report, props)
            if not any(overrides.get(k) for k in ("avoid", "hide_character", "drop_media", "reseed", "captions", "theme", "shorten", "remaster")):
                break
            attempts += 1
            overrides["reseed"] = attempts if overrides.get("reseed") else None
            repairs_log.append({"attempt": attempts, "overrides": overrides, "issues_before": summary["issue_count"],
                                "technical_pass_before": summary["technical_pass"]})
            self.phase("REPAIRING", f"repair_attempt_{attempts}")
            for sid in overrides["avoid"]:
                scene = next((s for s in board.scenes if s.id == sid), None)
                if scene:
                    scene.qa.repairs += 1
                    scene.qa.status = "repaired"
            for sid, fields in overrides.get("shorten", {}).items():
                scene = next((x for x in board.scenes if x.id == sid), None)
                if scene:
                    from ..quality.quality_report import shorten
                    if "heading" in fields:
                        scene.heading = shorten(scene.heading, fields["heading"])
                    if "points" in fields:
                        scene.points = [shorten(x, fields["points"]) for x in scene.points]
                    if "label" in fields:
                        scene.label = shorten(scene.label, fields["label"])
                    scene.qa.status, scene.qa.repairs = "repaired", scene.qa.repairs + 1
            visual_change = any(overrides.get(k) for k in ("avoid", "hide_character", "drop_media", "reseed", "captions", "theme", "shorten"))
            if visual_change:
                props = self.build_props(board, narration, overrides=overrides)
                video = self.render(props)
            elif overrides.get("remaster"):
                self.master(video, from_master=True)
        _save(self.folder / "qa" / "repairs.json", repairs_log)
        for scene in board.scenes:
            if scene.qa.status == "pending":
                scene.qa.status = "fail" if scene.id in report["summary"]["failing_scenes"] else "pass"
        return report, props

    # ---------- orchestration ----------
    def run(self, request: dict) -> dict:
        total_started = time.time()
        mode = request.get("mode", "local")
        if request.get("approved_budget_usd") and not (self.folder / "approvals.json").exists():
            self.costs.approve(self.folder, None, float(request["approved_budget_usd"]), approver="create_hybrid_video")
        board = self.direct(request)
        self.phase("PLANNING", "planning_scenes")
        estimate = self.estimate(board, mode)
        if request.get("dry_run"):
            self.finalize(board, None, None, None, estimate, mode, dry_run=True)
            return job_state.transition(self.folder, "COMPLETED", stage="dry_run_done", dry_run=True, review_required=True,
                                        storyboard=str(self.folder / "storyboard.json"), estimate=estimate)
        board = self.generate_assets(board, mode)
        board = self.attach_motion_clips(board)
        _save(self.folder / "storyboard.json", board.model_dump())
        narration = self.narrate(board, self.cfg.frame_rate)
        props = self.build_props(board, narration)
        _save(self.folder / "plan.json", to_plan_dict(board))
        video = self.render(props)
        report, props = self.qa_and_repair(board, narration, props, video)
        _save(self.folder / "storyboard.json", board.model_dump())
        checks = {"passed": report["summary"]["technical_pass"], "width": report["technical"]["width"], "height": report["technical"]["height"],
                  "has_audio": report["technical"]["has_audio"], "duration_seconds": report["technical"]["duration_seconds"],
                  "qa_summary": str(self.folder / "qa" / "summary.md")}
        _save(self.folder / "checks.json", checks)
        self.timings["total_wall_clock"] = round(time.time() - total_started + self.timings.get("total_wall_clock", 0), 2)
        _save(self.folder / "timings.json", self.timings)
        self.finalize(board, narration, props, report, estimate, mode)
        if board.cta:
            from ..creative import cta as cta_engine
            cta_engine.write_resources(self.folder, board, request.get("topic") or _load(self.folder / "topic.json"))
        if self.cfg.quality_control.require_technical_pass and not checks["passed"]:
            failures = [c["check"] for c in report["summary"]["mandatory_failures"]] or ["technical"]
            raise RuntimeError(f"Mandatory QA checks failed after repairs: {', '.join(failures)}")
        return job_state.transition(self.folder, "COMPLETED", stage="done", video=str(self.folder / "video.mp4"),
                                    poster=str(self.folder / "poster.jpg"), plan=str(self.folder / "plan.json"), checks=checks,
                                    review_required=True, mode=mode, qa=str(self.folder / "qa" / "summary.md"),
                                    degraded=[s.id for s in board.scenes if s.qa.status in ("fallback", "fail")])

    def finalize(self, board: Storyboard, narration, props, report, estimate, mode, dry_run=False):
        cost = self.costs.job_report(self.job_id)
        cache_hits = [d for d in self.decisions if d.get("stage") == "cinematic" and d.get("cached")]
        cost.update({"estimate": estimate, "local_timings_seconds": self.timings,
                     "cache_hits": len(cache_hits), "claude_usage": _load(self.folder / "claude_usage.json", []),
                     "note": "Local stages (Ollama, Kokoro/espeak, Remotion, FFmpeg) have no external cost."})
        _save(self.folder / "costs.json", cost)
        engines = sorted({n["engine"] for n in narration}) if narration else []
        timing = sorted({n["timing_source"] for n in narration}) if narration else []
        _save(self.folder / "provenance.json", {
            "schema_version": "2.0", "mode": mode, "dry_run": dry_run,
            "sources": [s.model_dump() for s in board.sources], "claims": [c.model_dump() for c in board.claims],
            "director": board.director, "decisions": self.decisions,
            # V1 keys kept for existing consumers
            "model": board.director.get("model", self.cfg.model), "voice_model": "hexgrad/Kokoro-82M" if "kokoro" in engines else
                          "Kokoro-82M v1.0 ONNX (kokoro-onnx model-files-v1.0)" if "kokoro_onnx" in engines else "espeak-ng",
            "voice": self.cfg.voice if {"kokoro", "kokoro_onnx"} & set(engines) else self.cfg.narration.espeak_voice, "voice_engines": engines,
            "caption_timing": timing, "narration_language": "English (US)", "visual_style": (props or {}).get("style", "studio"),
            "theme": (props or {}).get("theme"), "variant": (props or {}).get("variant"), "layouts": (props or {}).get("_layouts"),
            "scene_transitions": "beat-level 9-frame transitions; scenes butt-joined",
            "assets": [{"scene": s.id, **a.model_dump()} for s in board.scenes for a in s.assets],
            "music": "procedural bed generated locally (no third-party audio)" if self.cfg.music else "disabled",
            "audio_processing": "Voice high-passed, compressed, -16 LUFS; music ducked under speech; final mix -14 LUFS with limiter",
            "created_at": time.time(),
            "review": "Technical checks are automated. Factual accuracy, pronunciation and editorial quality need human review."})

    # ---------- post-hoc review / repair of an existing job ----------
    def _existing(self):
        board = Storyboard.model_validate_json((self.folder / "storyboard.json").read_text())
        narration = [_load(self.public / f"scene-{i}.json") for i in range(len(board.scenes))]
        if any(n is None for n in narration):
            raise RuntimeError("Narration records are missing for this job; re-run it with resume_job")
        props = _load(self.folder / "props.json")
        if not props or not (self.folder / "video.mp4").exists():
            raise RuntimeError("No rendered video to review")
        props.setdefault("_layouts", [b["layout"] for s in props["scenes"] for b in s["beats"]])
        return board, narration, props

    def review(self) -> dict:
        from ..quality import quality_report
        board, narration, props = self._existing()
        report = quality_report.run(self.folder / "video.mp4", props, narration, board.model_dump(), self.folder / "qa")
        return report["summary"]

    def repair(self) -> dict:
        board, narration, props = self._existing()
        job_state.transition(self.folder, "REPAIRING", stage="repair_requested")
        report, props = self.qa_and_repair(board, narration, props, self.folder / "video.mp4")
        _save(self.folder / "storyboard.json", board.model_dump())
        request = _load(self.folder / "request.json", {}) or {}
        self.finalize(board, narration, props, report, _load(self.folder / "estimate.json"), request.get("mode", "local"))
        checks = {"passed": report["summary"]["technical_pass"], "width": report["technical"]["width"], "height": report["technical"]["height"],
                  "has_audio": report["technical"]["has_audio"], "duration_seconds": report["technical"]["duration_seconds"]}
        _save(self.folder / "checks.json", checks)
        phase = "COMPLETED" if checks["passed"] or not self.cfg.quality_control.require_technical_pass else "FAILED"
        return job_state.transition(self.folder, phase, stage="repaired" if phase == "COMPLETED" else "repair_failed", checks=checks,
                                    state="completed" if phase == "COMPLETED" else "failed")
