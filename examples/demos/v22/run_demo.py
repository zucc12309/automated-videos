"""V2.2 demos A–D through the real pipeline with the FIELDNOTES premium renderer and the character on.

A  4 Claude Code repos (roundup, supplied storyboard, verified GitHub metadata)  → LINK CTA      (local)
B  vibe-coding prompt before/after (curated tip, deterministic storyboard)      → PROMPT CTA    (local)
C  MCP architecture (supplied storyboard, claims checked against the source)    → GUIDE CTA     (local)
D  hybrid cinematic "future of AI-assisted development"                         → MOCK cinematic provider:
   local FFmpeg clips stand in for Higgsfield; no network call, no money. Labelled mock everywhere.

Outputs are collected into demos/v22/<letter>/ (MP4 is gitignored; poster, contact sheet and JSON are kept).
Usage: .venv/bin/python examples/demos/v22/run_demo.py A [B C D]
"""
import fcntl
import json
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

from video_mcp import engine, settings, sources
from video_mcp.orchestration.pipeline import Pipeline

HERE = Path(__file__).parent
OUT = engine.ROOT / "demos" / "v22"
DEMOS = {
    "A": {"storyboard": "storyboard_a_claude_code_repos.json", "topic": "../topic_d_claude_code_repos.json", "mode": "local"},
    "B": {"vibe": "vibe-scope-ui", "mode": "local"},
    "C": {"storyboard": "storyboard_c_mcp_architecture.json", "topic": "topic_c_mcp_architecture.json", "mode": "local"},
    "D": {"storyboard": "storyboard_d_future_hybrid.json", "mode": "hybrid", "mock": True},
}
KEEP = ["storyboard.json", "decisions.json", "verification.json", "costs.json", "estimate.json", "timings.json", "provenance.json",
        "checks.json", "props.json", "poster.jpg"]


def config(mock: bool):
    raw = json.loads((engine.ROOT / "config.json").read_text())
    raw["production"].update(theme="fieldnotes-premium", style="premium", character="on")
    if mock:
        raw["cinematic"].update(enabled=True, provider="mock", usd_per_second_upper_bound=0.05, poll_interval_seconds=0)
        raw["budget"].update(allow_paid_generation=True, approval_policy="explicit", max_usd_per_video=1.0)
    return settings.from_dict(raw)


def contact_sheet(video: Path, dest: Path, count: int = 12) -> None:
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                               capture_output=True, text=True, check=True).stdout)
    fps = count / dur
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-vf",
                    f"fps={fps:.5f},scale=270:-1,drawtext=text='%{{pts\\:hms}}':x=8:y=8:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.5,tile=6x2",
                    "-frames:v", "1", str(dest)], check=True)


def run(letter: str) -> dict:
    spec = DEMOS[letter]
    cfg = config(spec.get("mock", False))
    ident = uuid.uuid4().hex[:12]
    folder = engine.job_path(ident)
    folder.mkdir(parents=True)
    request = {"mode": spec["mode"], "seed": f"v22-{letter}", "schema": 2, "plan": None, "topic_id": None, "autopilot": False,
               "dry_run": False, "approved_budget_usd": 0.5 if spec.get("mock") else 0,
               "demo_note": f"V2.2 demo {letter}" + (" — MOCK cinematic provider (no Higgsfield call)" if spec.get("mock") else "")}
    if "storyboard" in spec:
        request["storyboard"] = json.loads((HERE / spec["storyboard"]).read_text())
        request["topic"] = json.loads((HERE / spec["topic"]).read_text()) if spec.get("topic") else None
    else:
        topic = next(t for t in sources.vibe_topics(set()) if t["id"] == spec["vibe"])
        engine.save(folder / "topic.json", topic)
        request["topic"] = topic
    engine.save(folder / "request.json", request)
    engine.update(ident, id=ident, state="running", phase="CREATED", stage=f"v22_{letter}", created_at=time.time(), mode=spec["mode"])
    started = time.time()
    with (engine.DATA / "render.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        result = Pipeline(ident, root=engine.ROOT, data=engine.DATA, cfg=cfg).run(request)
    dest = OUT / letter
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    for name in KEEP:
        if (folder / name).exists():
            shutil.copy(folder / name, dest / name)
    for sub in ("qa", "resources"):
        if (folder / sub).exists():
            shutil.copytree(folder / sub, dest / sub)
    video = folder / "video.mp4"
    if video.exists():
        shutil.copy(video, dest / "video.mp4")
        contact_sheet(video, dest / "contact_sheet.jpg")
    summary = {"demo": letter, "job": ident, "state": result.get("state"), "phase": result.get("phase"), "degraded": result.get("degraded"),
               "wall_seconds": round(time.time() - started, 1), "mock_cinematic": bool(spec.get("mock")),
               "live_provider_tested": False, "qa": result.get("qa")}
    engine.save(dest / "summary.json", summary)
    return summary


if __name__ == "__main__":
    for letter in sys.argv[1:] or list(DEMOS):
        print(json.dumps(run(letter.upper()), indent=1, default=str))
