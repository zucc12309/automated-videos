"""Budget enforcement for paid providers: approvals, atomic reservations, reconciliation and per-job cost reports.

Rules (see docs/COST_CONTROLS.md):
* `budget.allow_paid_generation` is a master switch; when false no paid call is ever made.
* `approval_policy`:
    deny                -> no paid calls
    explicit            -> the job must carry an explicit approval (approved budget or per-request approval)
    auto_within_budget  -> unattended spending allowed inside the per-video/day caps
* Unknown cost is never zero: a request without an estimate needs an explicit per-request approval with a USD cap,
  and that cap is what gets reserved.
* Reservations are written under an exclusive file lock, so concurrent jobs cannot overspend the daily cap.
"""
from __future__ import annotations

import fcntl
import json
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from ..settings import Settings

# Anthropic first-party API list prices, USD per 1M tokens (skill model table cached 2026-10-06; verify before relying
# on them for billing). cache_write = 1.25x input for the 5-minute TTL.
CLAUDE_PRICES = {
    "claude-opus-5-5": {"input": 4.0, "output": 20.0, "cache_read": 0.20, "cache_write": 5.0},
    "claude-sonnet-5-5": {"input": 2.0, "output": 10.0, "cache_read": 0.20, "cache_write": 2.5},
    "claude-haiku-5-5": {"input": 0.10, "output": 0.50, "cache_read": 0.01, "cache_write": 0.125},
    "claude-fable-5-1": {"input": 10.0, "output": 50.0, "cache_read": 0.25, "cache_write": 12.5},
}
PRICING_SOURCE = "Anthropic API list prices as cached 2026-10-06; verify at https://www.anthropic.com/pricing"


class BudgetExceeded(RuntimeError):
    pass


class ApprovalRequired(RuntimeError):
    def __init__(self, request: dict):
        super().__init__(f"Approval required for {request['provider']} ({request['kind']}), estimate {request.get('estimate_usd')}")
        self.request = request


class PaidGenerationDisabled(RuntimeError):
    pass


def claude_cost(model: str, input_tokens=0, output_tokens=0, cache_read=0, cache_write=0) -> float | None:
    price = CLAUDE_PRICES.get(model)
    if not price:
        return None
    return round((input_tokens * price["input"] + output_tokens * price["output"] + cache_read * price["cache_read"]
                  + cache_write * price["cache_write"]) / 1_000_000, 6)


def claude_upper_bound(model: str, prompt_chars: int, max_output_tokens: int) -> float | None:
    """Conservative pre-call estimate: ~3 chars/token for input (overestimates English), full max_tokens of output."""
    return claude_cost(model, input_tokens=int(prompt_chars / 3) + 500, output_tokens=max_output_tokens)


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class CostController:
    def __init__(self, data_dir: Path, settings: Settings):
        self.dir = data_dir / "budget"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "ledger.json"
        self.settings = settings

    # ---------- storage ----------
    @contextmanager
    def _locked(self):
        with (self.dir / "ledger.lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            data = json.loads(self.path.read_text()) if self.path.exists() else {"reservations": {}, "entries": []}
            yield data
            temp = self.path.with_suffix(f".{uuid.uuid4().hex}.tmp")
            temp.write_text(json.dumps(data, indent=1))
            temp.replace(self.path)

    def _read(self) -> dict:
        return json.loads(self.path.read_text()) if self.path.exists() else {"reservations": {}, "entries": []}

    @staticmethod
    def _open_usd(data: dict, *, day: str | None = None, job: str | None = None) -> float:
        total = 0.0
        for r in data["reservations"].values():
            if r["status"] == "released" or (day and r["day"] != day) or (job and r["job_id"] != job):
                continue
            total += r["actual_usd"] if r["status"] == "committed" else r["usd"]
        return round(total, 6)

    def spent_today(self) -> float:
        return self._open_usd(self._read(), day=today())

    def spent_for_job(self, job_id: str) -> float:
        return self._open_usd(self._read(), job=job_id)

    def calls_for_job(self, job_id: str, provider: str) -> int:
        return sum(1 for r in self._read()["reservations"].values() if r["job_id"] == job_id and r["provider"] == provider
                   and r["status"] != "released")

    # ---------- approvals ----------
    @staticmethod
    def approvals(job_dir: Path) -> dict:
        path = job_dir / "approvals.json"
        return json.loads(path.read_text()) if path.exists() else {"job_cap_usd": 0.0, "approved": {}, "pending": {}, "denied": {}}

    @staticmethod
    def save_approvals(job_dir: Path, value: dict):
        path = job_dir / "approvals.json"
        temp = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
        temp.write_text(json.dumps(value, indent=1))
        temp.replace(path)

    def approve(self, job_dir: Path, request_id: str | None, max_usd: float, approver: str = "user") -> dict:
        """Record an explicit approval. request_id=None approves a job-level budget cap for all paid calls of this job."""
        if max_usd <= 0:
            raise ValueError("max_usd must be positive")
        ap = self.approvals(job_dir)
        if request_id:
            pending = ap["pending"].pop(request_id, None)
            if pending is None and request_id not in ap["approved"]:
                raise KeyError(f"No pending request {request_id}")
            ap["approved"][request_id] = {"max_usd": max_usd, "at": time.time(), "by": approver, "request": pending}
        else:
            ap["job_cap_usd"] = max(ap.get("job_cap_usd", 0.0), max_usd)
            ap["job_cap_at"] = time.time()
        self.save_approvals(job_dir, ap)
        return ap

    # ---------- the gate ----------
    def authorize(self, job_dir: Path, *, provider: str, kind: str, estimate_usd: float | None, request_key: str,
                  note: str = "") -> dict:
        """Check policy + caps, then atomically reserve. Returns the reservation. Raises on any reason not to spend."""
        b = self.settings.budget
        job_id = job_dir.name
        if not b.allow_paid_generation or b.approval_policy == "deny":
            raise PaidGenerationDisabled("Paid generation is disabled by config (budget.allow_paid_generation / approval_policy)")
        ap = self.approvals(job_dir)
        request_id = "req_" + request_key[:20]
        per_request = ap["approved"].get(request_id)
        if per_request:
            if estimate_usd is not None and estimate_usd > per_request["max_usd"]:
                raise ApprovalRequired(self._pending(job_dir, ap, request_id, provider, kind, estimate_usd,
                                                     f"estimate ${estimate_usd:.4f} exceeds approved ${per_request['max_usd']:.4f}"))
            amount = float(per_request["max_usd"] if estimate_usd is None else estimate_usd)
        elif estimate_usd is None:
            raise ApprovalRequired(self._pending(job_dir, ap, request_id, provider, kind, None, note))
        else:
            amount = float(estimate_usd)
        with self._locked() as data:
            job_open = self._open_usd(data, job=job_id)
            day_open = self._open_usd(data, day=today())
            if job_open + amount > b.max_usd_per_video + 1e-9:
                raise BudgetExceeded(f"Per-video cap ${b.max_usd_per_video:.2f} would be exceeded (open ${job_open:.4f} + ${amount:.4f})")
            if day_open + amount > b.max_usd_per_day + 1e-9:
                raise BudgetExceeded(f"Daily cap ${b.max_usd_per_day:.2f} would be exceeded (open ${day_open:.4f} + ${amount:.4f})")
            # Under the explicit policy a call without its own approval must fit inside the job's approved cap.
            pending_needed = (b.approval_policy == "explicit" and not per_request
                              and job_open + amount > float(ap.get("job_cap_usd") or 0) + 1e-9)
            if not pending_needed:
                res_id = "res_" + uuid.uuid4().hex[:12]
                data["reservations"][res_id] = {"id": res_id, "job_id": job_id, "provider": provider, "kind": kind, "usd": round(amount, 6),
                                                "actual_usd": 0.0, "status": "reserved", "day": today(), "created_at": time.time(),
                                                "request_id": request_id, "estimate_known": estimate_usd is not None, "note": note[:200]}
                return dict(data["reservations"][res_id])
        raise ApprovalRequired(self._pending(job_dir, ap, request_id, provider, kind, estimate_usd, note))

    def _pending(self, job_dir, ap, request_id, provider, kind, estimate, note) -> dict:
        request = {"request_id": request_id, "job_id": job_dir.name, "provider": provider, "kind": kind,
                   "estimate_usd": estimate, "estimate_known": estimate is not None, "note": note[:300], "at": time.time()}
        ap["pending"][request_id] = request
        self.save_approvals(job_dir, ap)
        return request

    def commit(self, reservation_id: str, actual_usd: float | None, *, usage: dict | None = None) -> dict:
        """Reconcile a reservation with the confirmed cost. Unknown actual cost keeps the reserved (upper-bound) amount."""
        with self._locked() as data:
            r = data["reservations"][reservation_id]
            r["status"] = "committed"
            r["actual_usd"] = round(float(actual_usd if actual_usd is not None else r["usd"]), 6)
            r["actual_known"] = actual_usd is not None
            r["usage"] = usage or {}
            r["committed_at"] = time.time()
            data["entries"].append({"reservation": reservation_id, "job_id": r["job_id"], "provider": r["provider"],
                                    "usd": r["actual_usd"], "estimated": actual_usd is None, "day": r["day"], "at": time.time()})
            return dict(r)

    def release(self, reservation_id: str, reason: str = "") -> None:
        """Free a reservation for a call that provably did not happen (never for unknown-outcome submissions)."""
        with self._locked() as data:
            r = data["reservations"].get(reservation_id)
            if r and r["status"] == "reserved":
                r["status"], r["released_reason"] = "released", reason[:200]

    def job_report(self, job_id: str) -> dict:
        data = self._read()
        rows = [r for r in data["reservations"].values() if r["job_id"] == job_id]
        external = round(sum(r["actual_usd"] if r["status"] == "committed" else r["usd"] for r in rows if r["status"] != "released"), 6)
        return {"job_id": job_id, "total_external_usd": external,
                "reserved_open_usd": round(sum(r["usd"] for r in rows if r["status"] == "reserved"), 6),
                "reservations": rows, "pricing_source": PRICING_SOURCE,
                "caps": {"per_video": self.settings.budget.max_usd_per_video, "per_day": self.settings.budget.max_usd_per_day},
                "spent_today_usd": self._open_usd(data, day=today())}
