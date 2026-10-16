"""Test C — HYBRID cinematic reel: "The future of AI-powered coding".

Runs the real HYBRID pipeline (budget gate, approval, generation journal, asset cache, footage compositing, QA) with the
MOCK cinematic provider, which renders local FFmpeg clips instead of calling Higgsfield. The ledger records the mock's
configured rate so the budget path is exercised; no money is spent and no external call is made.

To use real Higgsfield footage instead: install higgsfield-client, set HF_KEY (or HF_API_KEY + HF_API_SECRET), set
cinematic.provider="higgsfield", cinematic.application and a verified cinematic.usd_per_second_upper_bound in config.json,
enable budget.allow_paid_generation, and pass --real. Real credits are spent only up to the approved amount.
Usage: .venv/bin/python examples/demos/demo_c_hybrid.py [--approve 0.5] [--real]
"""
import argparse
import fcntl
import json
import time
import uuid
from pathlib import Path

from video_mcp import engine, settings
from video_mcp.orchestration import job_state
from video_mcp.orchestration.pipeline import Paused, Pipeline

parser = argparse.ArgumentParser()
parser.add_argument("--approve", type=float, default=0.5, help="explicit USD approval for this job (0 = none)")
parser.add_argument("--real", action="store_true", help="use config.json as-is (real Higgsfield if configured)")
args = parser.parse_args()

raw = json.loads((engine.ROOT / "config.json").read_text())
if not args.real:
    raw["cinematic"].update(enabled=True, provider="mock", usd_per_second_upper_bound=0.05, poll_interval_seconds=0)
    raw["budget"].update(allow_paid_generation=True, approval_policy="explicit", max_usd_per_video=1.0)
cfg = settings.from_dict(raw)

board = json.loads((Path(__file__).parent / "storyboard_c_future_coding.json").read_text())
ident = uuid.uuid4().hex[:12]
folder = engine.job_path(ident)
folder.mkdir(parents=True)
request = {"storyboard": board, "mode": "hybrid", "approved_budget_usd": args.approve, "seed": "demo-c", "schema": 2,
           "plan": None, "topic_id": None, "autopilot": False, "dry_run": False,
           "demo_note": "mock cinematic provider" if not args.real else "config.json providers"}
engine.save(folder / "request.json", request)
engine.update(ident, id=ident, state="running", phase="CREATED", stage="demo_c", created_at=time.time(), mode="hybrid")
print("job", ident)
with (engine.DATA / "render.lock").open("w") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    try:
        result = Pipeline(ident, root=engine.ROOT, data=engine.DATA, cfg=cfg).run(request)
        print(json.dumps({k: result.get(k) for k in ("state", "phase", "video", "degraded", "qa")}, indent=2))
    except Paused as exc:
        job_state.transition(folder, "AWAITING_APPROVAL", stage="awaiting_approval", state="awaiting_approval", note=str(exc))
        print("paused:", exc)
print(json.dumps(json.loads((folder / "costs.json").read_text())["reservations"], indent=1) if (folder / "costs.json").exists() else "")
