from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid
from typing import Literal

import httpx
from pydantic import BaseModel, Field, field_validator, model_validator

from . import audio as audio_fx, prompts, security, settings as settings_mod, sources, variety
from .orchestration import job_state

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
JOBS = DATA / "jobs"
OLLAMA = "http://127.0.0.1:11434"


class Scene(BaseModel):
    heading: str = Field(min_length=1, max_length=65)
    narration: str = Field(min_length=1, max_length=500, description="Natural US English narration. One or two short spoken sentences.")
    caption: str = Field(min_length=1, max_length=500, description="Exact spoken sentence; used for word-synced captions")
    points: list[str] = Field(default_factory=list, max_length=3)
    visual: Literal["cards", "terminal", "flow", "meter", "hook", "repo", "doc", "outro"] = "cards"
    item: int = Field(default=0, ge=0, le=8, description="0 for hook/outro, otherwise the list number this scene covers")
    label: str = Field(default="", max_length=28, description="Short tag for the item, e.g. the repo name")
    emphasis: str = Field(default="", max_length=30, description="One word or short phrase copied from the narration to highlight on screen")
    stat: str = Field(default="", max_length=20, description="Optional number copied exactly from the narration, e.g. 8,743 or $150,000; empty if none")

    @model_validator(mode="after")
    def copy_narration_to_caption(self):
        if re.search(r"https?://|www\.", self.narration):
            raise ValueError("Keep URLs in source_urls, not narration")
        self.caption = self.narration
        # On-screen highlights must come from the spoken line; drop anything the model made up.
        if self.emphasis.strip().lower() not in self.narration.lower():
            self.emphasis = ""
        if not re.search(r"\d", self.stat) or self.stat.strip() not in self.narration:
            self.stat = ""
        return self

    @field_validator("points")
    @classmethod
    def short_points(cls, values):
        if any(len(x) > 65 for x in values):
            raise ValueError("Each point must be at most 65 characters")
        return values


class Repo(BaseModel):
    full_name: str = Field(max_length=140)
    owner: str = Field(max_length=60)
    name: str = Field(max_length=100)
    description: str = Field(default="", max_length=300)
    stars: int = Field(default=0, ge=0)
    language: str = Field(default="", max_length=40)
    topics: list[str] = Field(default_factory=list, max_length=6)


class Plan(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    scenes: list[Scene] = Field(min_length=2, max_length=10)
    source_urls: list[str] = Field(default_factory=list, max_length=10)
    style: Literal["auto", "studio", "paper", "editorial", "kinetic", "mascot", "fieldnotes"] = "auto"
    series: str = Field(default="", max_length=16, description="One word naming the listed items, e.g. REPOS")
    repos: list[Repo] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def require_english_copy(self):
        copy = " ".join(
            [self.title, *(scene.heading for scene in self.scenes),
             *(scene.narration for scene in self.scenes),
             *(point for scene in self.scenes for point in scene.points)]
        )
        if re.search(r"[\u0900-\u097f]", copy):
            raise ValueError("Video copy must be in English only")
        return self


def config():
    return json.loads((ROOT / "config.json").read_text())


def save(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    temp.replace(path)


def job_path(job_id):
    if not re.fullmatch(r"[a-f0-9]{12}", job_id):
        raise ValueError("Invalid job ID")
    return JOBS / job_id


def _completed(status: dict) -> bool:
    """A real finished video. Dry runs and failed/canceled jobs never mark a topic or repo as used."""
    return status.get("state") == "completed" and not status.get("dry_run")


def history_ids():
    return {json.loads(p.read_text()).get("topic_id") for p in JOBS.glob("*/status.json") if _completed(json.loads(p.read_text()))}


def used_repos():
    names = set()
    for path in JOBS.glob("*/status.json"):
        topic = path.parent / "topic.json"
        if _completed(json.loads(path.read_text())) and topic.exists():
            names |= {r["full_name"] for r in json.loads(topic.read_text()).get("repos", [])}
    return names


def discover(limit=10):
    cfg = config()
    roundups, repo_errors = sources.repo_roundups(cfg, used_repos(), history_ids())
    stories, story_errors = sources.stories(cfg, history_ids())
    results = roundups + stories
    save(DATA / "topics.json", results)
    return {"topics": results[:max(1, min(limit, 30))], "errors": repo_errors + story_errors,
            "basis": "GitHub API repo metadata and readmes; full article text where fetchable. Not fact-checked."}


def preferred_kind():
    formats = config().get("formats") or ["roundup", "story"]
    completed = len(history_ids() - {None})
    return formats[completed % len(formats)]


def ensure_ollama():
    try:
        httpx.get(f"{OLLAMA}/api/tags", timeout=2).raise_for_status()
        return
    except httpx.HTTPError:
        pass
    binary = shutil.which("ollama") or "/opt/homebrew/bin/ollama"
    DATA.mkdir(exist_ok=True)
    with (DATA / "ollama.log").open("a") as log:
        subprocess.Popen([binary, "serve"], stdout=log, stderr=log, start_new_session=True,
                         env={**os.environ, "OLLAMA_HOST": "127.0.0.1:11434", "OLLAMA_NO_CLOUD": "1"})
    for _ in range(30):
        try:
            httpx.get(f"{OLLAMA}/api/tags", timeout=1).raise_for_status()
            return
        except httpx.HTTPError:
            time.sleep(1)
    raise RuntimeError("Ollama did not start; see data/ollama.log")


def _norm(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _fallback_emphasis(scene: Scene) -> str:
    number = re.search(r"\$?\d[\d,.]*\s?(?:%|[KMB]\b|million|billion|thousand|GB|TB)?", scene.narration)
    if number:
        return number.group(0).strip()
    if scene.label and scene.label.lower() in scene.narration.lower():
        return scene.label
    words = [w.strip(".,!?;:'\"") for w in scene.narration.split()]
    return max(words, key=len) if words else ""


def unsupported_numbers(text: str, source: str) -> list[str]:
    """Digits in narration that never appear in the source (ignoring commas). Small counts like list sizes are allowed."""
    digits = {re.sub(r"[,]", "", n).rstrip(".") for n in re.findall(r"\d[\d,.]*", source)}
    found = [n.rstrip(".,") for n in re.findall(r"\d[\d,.]*", text)]
    return [n for n in found if re.sub(r",", "", n) not in digits and not (n.isdigit() and int(n) <= 10)]


def shape_plan(plan: Plan, topic: dict, count: int, strict: bool = True) -> Plan:
    """Enforce the hook / numbered items / outro structure and attach real repo data.
    strict=False fills missing highlights and points instead of asking the model to retry."""
    if len(plan.scenes) != count + 2:
        raise ValueError(f"Return exactly {count + 2} scenes: 1 hook, {count} numbered items, 1 outro")
    roundup = topic.get("kind") == "roundup"
    source_text = json.dumps(topic, ensure_ascii=False)
    for i, scene in enumerate(plan.scenes):
        scene.item = 0 if i in (0, count + 1) else i
        scene.visual = "hook" if i == 0 else "outro" if i == count + 1 else ("repo" if roundup else "doc")
        if roundup and scene.item:
            repo = topic["repos"][i - 1]
            spoken = _norm(scene.narration)
            if _norm(repo["name"]) not in spoken:
                if strict:
                    raise ValueError(f"Scene {i + 1} must say the repo name '{repo['name']}' in its narration")
                scene.narration = scene.caption = f"Number {i}: {re.sub(r'[-_]+', ' ', repo['name'])}. {scene.narration}"
            scene.label = repo["name"][:28]
        if scene.item and not scene.label:
            scene.label = scene.heading[:28]
        bad = unsupported_numbers(scene.narration, source_text)
        if bad and strict:
            raise ValueError(f"Scene {i + 1} uses numbers not in the source data: {', '.join(bad)}. Use only numbers from the data, or none.")
        if bad:
            kept = [x for x in re.split(r"(?<=[.!?])\s+", scene.narration) if not unsupported_numbers(x, source_text)]
            scene.narration = scene.caption = " ".join(kept) or re.sub(r"\d[\d,.]*", "", scene.narration)
            scene.stat = ""
        missing = []
        if not scene.emphasis:
            missing.append("emphasis")
        if scene.item and len(scene.points) < 2:
            missing.append("2-3 points")
        if missing and strict:
            raise ValueError(f"Scene {i + 1} is missing: {', '.join(missing)}. Every scene needs emphasis copied from its narration; numbered scenes need 2-3 short points.")
        if not scene.emphasis:
            scene.emphasis = _fallback_emphasis(scene)[:30]
        if scene.item and not scene.points:
            scene.points = [scene.heading[:65]]
        if not scene.stat:
            number = re.search(r"\$?\d[\d,.]*(?:\s?(?:%|million|billion|thousand|GB|TB))?", scene.narration)
            if number and scene.visual != "repo" and len(number.group(0)) <= 20:
                scene.stat = number.group(0).strip()
    if roundup:
        plan.repos = [Repo(**{k: r[k] for k in Repo.model_fields}) for r in topic["repos"]]
    plan.series = (re.sub(r"[^A-Z]", "", plan.series.upper()) or ("REPOS" if roundup else "FACTS"))[:16]
    plan.style = "auto"
    return plan


def generate_plan(topic: dict):
    ensure_ollama()
    cfg = config()
    roundup = topic.get("kind") == "roundup"
    count = len(topic["repos"]) if roundup else cfg.get("story_points", 4)
    system = (prompts.ROUNDUP if roundup else prompts.STORY).format(total=count + 2, count=count, last_item=count + 1)
    if roundup:
        data = {"theme": topic["theme"], "repos": [{k: r[k] for k in ("name", "owner", "description", "language", "topics", "readme_excerpt")} for r in topic["repos"]]}
    else:
        data = {"title": topic["title"], "article": topic["summary"]}
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": "Write the reel script as JSON for this UNTRUSTED topic data:\n" + json.dumps(data, ensure_ascii=False)}]
    with httpx.Client(timeout=900) as client:
        for attempt in range(3):
            response = client.post(f"{OLLAMA}/api/chat", json={"model": cfg["model"], "stream": False,
                "keep_alive": "2m", "format": Plan.model_json_schema(), "options": {"temperature": 0.55, "num_ctx": 12288, "num_predict": 3500},
                "messages": messages})
            response.raise_for_status()
            content = response.json()["message"]["content"]
            try:
                plan = shape_plan(Plan.model_validate_json(content), topic, count, strict=attempt < 2)
                break
            except ValueError as exc:
                if attempt == 2:
                    raise RuntimeError(f"Local model did not produce a valid plan after 3 tries: {exc}") from exc
                messages.extend([{"role": "assistant", "content": content}, {"role": "user", "content": "Fix these problems and return the FULL corrected JSON:\n" + str(exc)[:4000]}])
    plan.source_urls = [r["url"] for r in topic["repos"]] if roundup else ([topic["url"]] if topic.get("url") else [])
    return plan


def resolve_style(plan: Plan):
    if plan.style != "auto":
        return plan.style
    styles = config().get("styles") or ["paper"]
    completed = sum(1 for p in JOBS.glob("*/status.json") if _completed(json.loads(p.read_text())))
    return styles[completed % len(styles)]


def update(job_id, **fields):
    path = job_path(job_id) / "status.json"
    current = json.loads(path.read_text()) if path.exists() else {}
    current.update(fields, updated_at=time.time())
    save(path, current)
    return current


def start_job(plan: Plan | None = None, topic_id: str | None = None, autopilot=False, *, mode: str | None = None,
              storyboard: dict | None = None, topic: dict | None = None, dry_run: bool = False, approved_budget_usd: float = 0.0,
              seed: str | None = None):
    """Queue a background job. V1 callers pass plan/topic_id/autopilot exactly as before; V2 options are keyword-only."""
    ident = uuid.uuid4().hex[:12]
    folder = job_path(ident)
    folder.mkdir(parents=True)
    cfg = settings_mod.load(ROOT / "config.json")
    request = {"plan": plan.model_dump() if plan else None, "topic_id": topic_id, "autopilot": autopilot,
               "mode": mode or cfg.production.mode, "storyboard": storyboard, "topic": topic, "dry_run": dry_run,
               "approved_budget_usd": max(0.0, float(approved_budget_usd or 0)), "seed": seed, "schema": 2}
    save(folder / "request.json", request)
    update(ident, id=ident, state="queued", stage="waiting", phase="CREATED", created_at=time.time(), topic_id=topic_id,
           mode=request["mode"], dry_run=dry_run)
    return {"id": ident, "state": "queued", "pid": spawn(ident), "mode": request["mode"], "dry_run": dry_run, "next": "Poll job_status with this ID"}


def spawn(ident: str) -> int:
    folder = job_path(ident)
    with (folder / "worker.log").open("a") as log:
        process = subprocess.Popen([sys.executable, "-m", "video_mcp.engine", "worker", ident], cwd=ROOT,
                                   stdout=log, stderr=log, start_new_session=True, env=security.child_env(keep_secrets=True))
    update(ident, pid=process.pid)
    return process.pid


def resume_job(job_id: str) -> dict:
    """Restart an interrupted, failed or approval-paused job from its checkpoints (completed stages are not redone)."""
    current = status(job_id)
    if current["state"] in ("queued", "running"):
        return {"id": job_id, "resumed": False, "reason": "job is still active"}
    if current["state"] == "completed":
        return {"id": job_id, "resumed": False, "reason": "job already completed; use repair_video to change it"}
    if current["state"] == "canceled":
        return {"id": job_id, "resumed": False, "reason": "job was canceled"}
    (job_path(job_id) / "CANCEL").unlink(missing_ok=True)
    update(job_id, state="queued", stage="resuming", error=None, resumed_at=time.time())
    return {"id": job_id, "resumed": True, "pid": spawn(job_id), "checkpoints": sorted(job_state.checkpoints(job_path(job_id)))}


def status(job_id):
    folder = job_path(job_id)
    current = json.loads((folder / "status.json").read_text())
    if current["state"] in ("queued", "running") and current.get("pid"):
        try:
            os.kill(current["pid"], 0)
        except ProcessLookupError:
            current = update(job_id, state="failed", phase="FAILED", resumable=True,
                             error="Worker stopped unexpectedly; see worker.log. resume_job continues from the last checkpoint.")
    return current


def run_command(args, timeout=1800):
    subprocess.run(args, cwd=ROOT, check=True, timeout=timeout)


def produce(job_id, plan):
    """V1 entry point kept for compatibility: render a Plan through the V2 pipeline in LOCAL mode."""
    from .orchestration.pipeline import Pipeline
    return Pipeline(job_id, root=ROOT, data=DATA, cfg=settings_mod.load(ROOT / "config.json")).run({"plan": plan.model_dump(), "mode": "local"})


def check_video(path):
    result = subprocess.run(["ffprobe", "-v", "quiet", "-show_streams", "-show_format", "-of", "json", str(path)], capture_output=True, text=True, check=True)
    info = json.loads(result.stdout)
    video = next((s for s in info["streams"] if s["codec_type"] == "video"), {})
    audio = next((s for s in info["streams"] if s["codec_type"] == "audio"), {})
    duration = float(info.get("format", {}).get("duration", 0))
    cfg = config()
    return {"passed": bool(video.get("width") == cfg["width"] and video.get("height") == cfg["height"] and audio and duration > 1),
            "width": video.get("width"), "height": video.get("height"), "has_audio": bool(audio), "duration_seconds": duration}


def worker(job_id):
    from .orchestration.pipeline import Paused, Pipeline
    DATA.mkdir(exist_ok=True)
    folder = job_path(job_id)
    update(job_id, pid=os.getpid())
    with (DATA / "render.lock").open("w") as lock:
        # Serialize GPU/CPU-heavy jobs across MCP sessions and CLI invocations.
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            if job_state.cancel_requested(folder):
                raise job_state.Canceled("Canceled by user")
            update(job_id, state="running", stage="preparing")
            request = json.loads((folder / "request.json").read_text())
            cfg = settings_mod.load(ROOT / "config.json")
            if not request.get("plan") and not request.get("storyboard") and not (folder / "topic.json").exists():
                job_state.transition(folder, "DISCOVERING", stage="discovering_topics")
                if request.get("topic"):
                    topic = request["topic"]
                elif request["autopilot"]:
                    kind = preferred_kind()
                    topics = sorted(discover(10)["topics"], key=lambda t: t.get("kind") != kind)
                    topic = topics[0] if topics else None
                else:
                    topics = json.loads((DATA / "topics.json").read_text()) if (DATA / "topics.json").exists() else []
                    topics = [x for x in topics if x["id"] == request["topic_id"] and x["id"] not in history_ids()]
                    topic = topics[0] if topics else None
                if not topic:
                    raise RuntimeError("No fresh unused topic found; adjust feeds/keywords or submit a plan")
                topic.setdefault("retrieved_at", time.time())
                update(job_id, topic_id=topic["id"], topic_title=topic["title"])
                save(folder / "topic.json", topic)
            Pipeline(job_id, root=ROOT, data=DATA, cfg=cfg).run(request)
        except Paused as exc:
            job_state.transition(folder, "AWAITING_APPROVAL", stage="awaiting_approval", state="awaiting_approval", error=None,
                                 pending=list(json.loads((folder / "approvals.json").read_text()).get("pending", {}).values())
                                 if (folder / "approvals.json").exists() else [], note=str(exc))
        except job_state.Canceled as exc:
            job_state.transition(folder, "CANCELED", stage="canceled", error=str(exc))
        except Exception as exc:
            import traceback
            traceback.print_exc()
            update(job_id, state="failed", phase="FAILED", error=security.redact(str(exc))[:2000], stage="failed", resumable=True)


def background(job_id: str, action: str) -> dict:
    """Run review/repair for an existing job in a detached worker (returns immediately)."""
    folder = job_path(job_id)
    if not (folder / "status.json").exists():
        raise ValueError("Unknown job")
    with (folder / "worker.log").open("a") as log:
        process = subprocess.Popen([sys.executable, "-m", "video_mcp.engine", action, job_id], cwd=ROOT, stdout=log, stderr=log,
                                   start_new_session=True, env=security.child_env(keep_secrets=True))
    return {"id": job_id, "action": action, "pid": process.pid, "next": "Poll job_status / get_video_report"}


def post_worker(job_id: str, action: str):
    from .orchestration.pipeline import Pipeline
    folder = job_path(job_id)
    cfg = settings_mod.load(ROOT / "config.json")
    lock_path = DATA / "render.lock"
    try:
        if action == "review":
            summary = Pipeline(job_id, root=ROOT, data=DATA, cfg=cfg).review()
            update(job_id, last_review={"at": time.time(), "technical_pass": summary["technical_pass"], "issues": summary["issue_count"]})
            return
        with lock_path.open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            Pipeline(job_id, root=ROOT, data=DATA, cfg=cfg).repair()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        update(job_id, **{f"last_{action}_error": security.redact(str(exc))[:1000]})
    finally:
        (folder / f"{action}.done").write_text(str(time.time()))


def _v2_health() -> dict:
    from . import tts
    from .providers.claude_provider import ClaudeProvider
    from .providers.higgsfield_provider import HiggsfieldProvider
    cfg = settings_mod.load(ROOT / "config.json")
    try:
        narration = "%s (%s)" % tts.available_engine(cfg.narration.engine)
    except RuntimeError as exc:
        narration = f"unavailable: {exc}"
    return {"production_mode": cfg.production.mode, "narration_engine": narration,
            "claude": {"model": cfg.claude_model(), "ready": ClaudeProvider(cfg).available()[1]},
            "higgsfield": {"ready": HiggsfieldProvider(cfg).available()[1]},
            "paid_generation_enabled": cfg.budget.allow_paid_generation, "approval_policy": cfg.budget.approval_policy,
            "browser_executable": cfg.browser() or "remotion default"}


def health():
    try:
        response = httpx.get(f"{OLLAMA}/api/tags", timeout=3)
        response.raise_for_status()
        models = [x["name"] for x in response.json()["models"]]
    except Exception:
        models = []
    cfg = config()
    return {"root": str(ROOT), "ffmpeg": shutil.which("ffmpeg"), "espeak": shutil.which("espeak-ng"),
            "renderer_installed": (ROOT / "node_modules/.bin/remotion").exists(), "ollama_models": models,
            "configured_model": cfg["model"], "model_ready": cfg["model"] in models, "voice": cfg["voice"],
            "narration_language": "English (US)", "tts_language_code": cfg["tts_language_code"],
            "api_keys_required": False, "schedule_enabled": False, **_v2_health(),
            "notes": "First speech run downloads public model weights. Discovery needs internet. Rendering and cached inference are local."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["worker", "health", "discover", "autopilot", "render", "status", "review", "repair",
                                            "resume", "preview", "report"])
    parser.add_argument("value", nargs="?")
    args = parser.parse_args()
    if args.command == "worker":
        worker(args.value)
        return
    if args.command in ("review", "repair"):
        post_worker(args.value, args.command)
        return
    if args.command == "health":
        result = health()
    elif args.command == "discover":
        result = discover()
    elif args.command == "autopilot":
        result = start_job(autopilot=True)
    elif args.command == "render":
        result = start_job(plan=Plan.model_validate_json(Path(args.value).read_text()))
    elif args.command == "resume":
        result = resume_job(args.value)
    elif args.command == "preview":
        from .orchestration import tools
        result = tools.preview_storyboard(plan=json.loads(Path(args.value).read_text()))
    elif args.command == "report":
        from .orchestration import tools
        result = tools.video_report(args.value)
    else:
        result = status(args.value)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
