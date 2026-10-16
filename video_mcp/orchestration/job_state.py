"""Persistent job state machine and checkpoints.

`status.json` keeps the V1 contract (`state` in queued|running|completed|failed, free-text `stage`) and gains:
  phase        fine-grained V2 state (below)
  history      [{phase, at}] transitions
  checkpoints  stage -> {at, artifacts} written by the pipeline, used to resume after a crash
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

PHASES = ["CREATED", "DISCOVERING", "RESEARCHING", "SCRIPTING", "DIRECTING", "PLANNING", "AWAITING_APPROVAL",
          "GENERATING_ASSETS", "SYNTHESIZING_AUDIO", "ALIGNING", "RENDERING", "VALIDATING", "REPAIRING",
          "COMPLETED", "FAILED", "CANCELED"]
TERMINAL = {"COMPLETED", "FAILED", "CANCELED"}
WORK = PHASES[1:13]

# Any working phase may advance to a later working phase (stages are skipped when not needed, e.g. no cinematic assets),
# pause for approval, repair, or end. AWAITING_APPROVAL resumes into any working phase. REPAIRING loops to RENDERING.
_ALLOWED: dict[str, set[str]] = {"CREATED": set(WORK) | {"FAILED", "CANCELED"}}
for i, phase in enumerate(WORK):
    _ALLOWED[phase] = set(WORK[i:]) | {"AWAITING_APPROVAL", "FAILED", "CANCELED", "COMPLETED"}
_ALLOWED["AWAITING_APPROVAL"] = set(WORK) | {"FAILED", "CANCELED"}
_ALLOWED["REPAIRING"] |= {"RENDERING", "VALIDATING", "GENERATING_ASSETS", "SYNTHESIZING_AUDIO"}
_ALLOWED["VALIDATING"] |= {"REPAIRING"}
# Terminal jobs can be explicitly re-opened by repair_video / resume_job.
_ALLOWED["FAILED"] = {"REPAIRING", "CREATED", *WORK}
_ALLOWED["COMPLETED"] = {"REPAIRING", "VALIDATING"}
_ALLOWED["CANCELED"] = set()

LEGACY_STATE = {"COMPLETED": "completed", "FAILED": "failed", "CANCELED": "canceled", "AWAITING_APPROVAL": "awaiting_approval",
                "CREATED": "queued"}


class InvalidTransition(RuntimeError):
    pass


def can_transition(current: str | None, new: str) -> bool:
    if current is None or current == new:
        return True
    return new in _ALLOWED.get(current, set())


def _save(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    temp.replace(path)


def transition(folder: Path, phase: str, **fields) -> dict:
    if phase not in PHASES:
        raise ValueError(f"Unknown phase {phase}")
    path = folder / "status.json"
    current = json.loads(path.read_text()) if path.exists() else {}
    if not can_transition(current.get("phase"), phase):
        raise InvalidTransition(f"{current.get('phase')} -> {phase} is not allowed")
    history = current.get("history", [])
    if current.get("phase") != phase:
        history.append({"phase": phase, "at": time.time()})
    state = LEGACY_STATE.get(phase, "running")
    current.update(fields, phase=phase, state=fields.get("state", state), history=history[-60:], updated_at=time.time())
    _save(path, current)
    return current


def checkpoint(folder: Path, stage: str, **artifacts) -> None:
    path = folder / "checkpoints.json"
    data = json.loads(path.read_text()) if path.exists() else {}
    data[stage] = {"at": time.time(), **artifacts}
    _save(path, data)


def checkpoints(folder: Path) -> dict:
    path = folder / "checkpoints.json"
    return json.loads(path.read_text()) if path.exists() else {}


def cancel_requested(folder: Path) -> bool:
    return (folder / "CANCEL").exists()


def request_cancel(folder: Path) -> dict:
    (folder / "CANCEL").write_text(str(time.time()))
    status = json.loads((folder / "status.json").read_text())
    pid = status.get("pid")
    if status.get("phase") in TERMINAL or status.get("state") in ("completed", "failed", "canceled"):
        return {"id": folder.name, "canceled": False, "reason": f"job already {status.get('state')}"}
    if status.get("state") in ("queued", "awaiting_approval") or not pid:
        return {"id": folder.name, "canceled": True, **transition(folder, "CANCELED", stage="canceled", error="Canceled by user")}
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return {"id": folder.name, "canceled": True, **transition(folder, "CANCELED", stage="canceled", error="Canceled by user")}
    # Running worker polls the CANCEL marker between stages and stops itself.
    return {"id": folder.name, "canceled": True, "pending": True, "note": "Worker stops at the next stage boundary."}


class Canceled(RuntimeError):
    pass
