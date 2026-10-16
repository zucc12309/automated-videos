"""Providers, budget enforcement, cinematic generation and failure handling — all external services mocked."""
import json
import multiprocessing as mp
import subprocess
from pathlib import Path
from types import SimpleNamespace as N

import pytest

from video_mcp import engine
from video_mcp.creative import director
from video_mcp.orchestration import pipeline as pipeline_mod
from video_mcp.orchestration.asset_manager import AssetManager, cache_key, probe_video
from video_mcp.orchestration.cost_controller import (ApprovalRequired, BudgetExceeded, CostController, PaidGenerationDisabled,
                                                     claude_cost, claude_upper_bound)
from video_mcp.providers.base import CinematicRequest, ProviderError
from video_mcp.providers.claude_provider import ClaudeProvider
from video_mcp.providers.higgsfield_provider import HiggsfieldProvider, MockCinematicProvider, _find_video_url
from video_mcp.providers.script_providers import TemplateProvider
from video_mcp.schemas import storyboard as sb

from conftest import have

PAID = {"allow_paid_generation": True, "approval_policy": "explicit", "max_usd_per_video": 1.0, "max_usd_per_day": 2.0}


# ---------- pricing ----------

def test_claude_cost_math_and_unknown_models():
    assert claude_cost("claude-opus-5-5", 1_000_000, 1_000_000) == 24.0
    assert claude_cost("claude-opus-5-5", 0, 0, cache_read=1_000_000) == .2
    assert claude_cost("some-new-model", 10, 10) is None
    assert claude_upper_bound("claude-opus-5-5", 3000, 1000) > claude_cost("claude-opus-5-5", 1000, 1000)


# ---------- cost controller ----------

def test_paid_generation_disabled_by_default(tmp_path, make_cfg, job_dir):
    ctl = CostController(tmp_path, make_cfg())
    with pytest.raises(PaidGenerationDisabled):
        ctl.authorize(job_dir, provider="claude", kind="x", estimate_usd=.1, request_key="k")


def test_explicit_policy_requires_approval_then_reserves(tmp_path, make_cfg, job_dir):
    ctl = CostController(tmp_path, make_cfg(budget=PAID))
    with pytest.raises(ApprovalRequired) as exc:
        ctl.authorize(job_dir, provider="higgsfield", kind="cinematic", estimate_usd=.3, request_key="abc")
    assert exc.value.request["request_id"] in ctl.approvals(job_dir)["pending"]
    ctl.approve(job_dir, None, .5)
    r = ctl.authorize(job_dir, provider="higgsfield", kind="cinematic", estimate_usd=.3, request_key="abc")
    assert r["status"] == "reserved" and ctl.spent_for_job(job_dir.name) == .3
    with pytest.raises(ApprovalRequired):     # second call would exceed the approved $0.50 job budget
        ctl.authorize(job_dir, provider="higgsfield", kind="cinematic", estimate_usd=.3, request_key="def")
    ctl.commit(r["id"], .25)
    assert ctl.spent_for_job(job_dir.name) == .25


def test_unknown_cost_is_never_zero(tmp_path, make_cfg, job_dir):
    ctl = CostController(tmp_path, make_cfg(budget={**PAID, "approval_policy": "auto_within_budget"}))
    with pytest.raises(ApprovalRequired) as exc:
        ctl.authorize(job_dir, provider="higgsfield", kind="cinematic", estimate_usd=None, request_key="zz")
    req = exc.value.request
    assert req["estimate_known"] is False
    ctl.approve(job_dir, req["request_id"], .4)
    r = ctl.authorize(job_dir, provider="higgsfield", kind="cinematic", estimate_usd=None, request_key="zz")
    assert r["usd"] == .4 and r["estimate_known"] is False
    ctl.commit(r["id"], None)     # actual unknown -> keep the approved upper bound
    assert ctl.spent_for_job(job_dir.name) == .4


def test_per_video_and_daily_caps(tmp_path, make_cfg, job_dir):
    ctl = CostController(tmp_path, make_cfg(budget={**PAID, "approval_policy": "auto_within_budget"}))
    with pytest.raises(BudgetExceeded):
        ctl.authorize(job_dir, provider="claude", kind="x", estimate_usd=1.2, request_key="a")
    other = job_dir.parent / "bbbbbbbbbbbb"
    other.mkdir()
    ctl.authorize(job_dir, provider="claude", kind="x", estimate_usd=.9, request_key="a")
    ctl.authorize(other, provider="claude", kind="x", estimate_usd=.9, request_key="b")
    third = job_dir.parent / "cccccccccccc"
    third.mkdir()
    with pytest.raises(BudgetExceeded, match="Daily"):
        ctl.authorize(third, provider="claude", kind="x", estimate_usd=.5, request_key="c")


def test_release_frees_reservation_and_report(tmp_path, make_cfg, job_dir):
    ctl = CostController(tmp_path, make_cfg(budget={**PAID, "approval_policy": "auto_within_budget"}))
    r = ctl.authorize(job_dir, provider="claude", kind="x", estimate_usd=.5, request_key="a")
    ctl.release(r["id"], "400 before billing")
    report = ctl.job_report(job_dir.name)
    assert report["total_external_usd"] == 0 and report["reservations"][0]["status"] == "released"


def _reserve_worker(args):
    data_dir, cfg_raw, n = args
    from video_mcp import settings
    ctl = CostController(Path(data_dir), settings.from_dict(cfg_raw))
    folder = Path(data_dir) / "jobs" / f"{n:012x}"
    folder.mkdir(parents=True, exist_ok=True)
    try:
        ctl.authorize(folder, provider="higgsfield", kind="cinematic", estimate_usd=.3, request_key=str(n))
        return 1
    except BudgetExceeded:
        return 0


def test_concurrent_jobs_cannot_overspend_daily_cap(tmp_path, cfg_dict):
    raw = {**cfg_dict, "budget": {**PAID, "approval_policy": "auto_within_budget", "max_usd_per_day": 1.0}}
    with mp.get_context("fork").Pool(8) as pool:
        granted = sum(pool.map(_reserve_worker, [(str(tmp_path), raw, n) for n in range(16)]))
    assert granted == 3                     # 3 x $0.30 fits under $1.00; a 4th would not
    ledger = json.loads((tmp_path / "budget" / "ledger.json").read_text())
    assert round(sum(r["usd"] for r in ledger["reservations"].values()), 2) == .9


# ---------- Claude provider (mocked API) ----------

def _director_output(**overrides):
    scene = lambda narr, intent="generic", **kw: {"narration": narr, "heading": "Heading", "points": ["Point one", "Point two"], "emphasis": narr.split()[0],
                                                  "stat": "", "label": "Label", "visual_intent": "explain", "intent": intent, "render_engine": "remotion",
                                                  "layout": "", "entrance": "reveal", "emphasis_motion": "highlight", "camera": "subtle_push",
                                                  "pace": "medium", "claim_ids": ["c1"], "code_lines": [], "steps": [], "compare_titles": [],
                                                  "compare_left": [], "compare_right": [], "nodes": [], "timeline": [], "cinematic_prompt": "",
                                                  "character": False, **kw}
    data = {"title": "Agents and tools", "series": "FACTS", "audience": "developers", "core_message": "m", "viewer_benefit": "b",
            "hook": "h", "tone": "premium editorial", "pacing": "dynamic", "theme": "midnight", "visual_identity": "v",
            "sound_design": "s", "call_to_action": "Save this.",
            "claims": [{"id": "c1", "text": "Agents call tools through a protocol.", "source_ids": ["src1"], "status": "verified"}],
            "scenes": [scene("Agents now call tools for you.", "hook"), scene("Agents call tools through a protocol.", "api_flow", nodes=["Agent", "Protocol", "Tool"]),
                       scene("Each tool returns results to the agent.", "architecture"), scene("Save this for later.", "recap")]}
    data.update(overrides)
    return data


class FakeMessages:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        text, stop = reply
        return N(content=[N(type="text", text=json.dumps(text) if not isinstance(text, str) else text)], stop_reason=stop,
                 usage=N(input_tokens=2000, output_tokens=1500, cache_read_input_tokens=1000, cache_creation_input_tokens=0),
                 model="claude-opus-5-5", id="msg_1", _request_id="req_1")


def _claude(make_cfg, replies, **cd):
    messages = FakeMessages(replies)
    client = N(beta=N(messages=messages))
    return ClaudeProvider(make_cfg(creative_director=cd or {}), client=client), messages


TOPIC = {"kind": "story", "title": "Agents and tools", "url": "https://example.com/a",
         "summary": "Agents call tools through a protocol. Each tool returns results to the agent. Agents now call tools for you."}


def test_claude_storyboard_success_with_usage_and_gate(make_cfg):
    from video_mcp.creative import research
    provider, messages = _claude(make_cfg, [(_director_output(), "end_turn")])
    packet, sources = research.build_research(TOPIC)
    settled = []
    board, usages = provider.direct(packet, topic=TOPIC, sources=sources, fmt="story", scene_count=4, target_seconds=40,
                                    cinematic_allowed=0, video_id="v", gate=lambda req: settled.append)
    call = messages.calls[0]
    assert call["model"] == "claude-opus-5-5" and call["fallbacks"] == "default"
    assert call["output_config"]["format"]["type"] == "json_schema" and call["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert "<research>" in call["messages"][0]["content"]
    assert board.creative_direction.theme == "midnight" and board.scenes[1].intent == "api_flow" and board.scenes[1].visual.nodes
    assert usages[0].cost_usd == pytest.approx((2000 * 4 + 1500 * 20 + 1000 * .2) / 1e6)
    assert settled and settled[0] is usages[0]


def test_claude_invalid_output_is_revised_then_accepted(make_cfg):
    bad = _director_output()
    bad["scenes"][1]["narration"] = "Agents call 4,500 tools through a protocol."
    provider, messages = _claude(make_cfg, [("{not json", "end_turn"), (bad, "end_turn"), (_director_output(), "end_turn")])
    from video_mcp.creative import research
    packet, sources = research.build_research(TOPIC)
    board, usages = provider.direct(packet, topic=TOPIC, sources=sources, fmt="story", scene_count=4, target_seconds=40,
                                    cinematic_allowed=0, video_id="v")
    assert len(messages.calls) == 3 and "4,500" in messages.calls[2]["messages"][-1]["content"]
    assert board.director["attempts"] == 3


def test_claude_errors_are_classified(make_cfg):
    import anthropic
    import httpx
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    rate = anthropic.RateLimitError("slow down", response=httpx.Response(429, request=req, headers={"retry-after": "7"}), body=None)
    provider, _ = _claude(make_cfg, [rate])
    with pytest.raises(ProviderError) as exc:
        provider.call(provider.build_request({}, fmt="story", scene_count=4, target_seconds=40, cinematic_allowed=0))
    assert exc.value.kind == "rate_limit" and exc.value.retry_after == 7 and exc.value.retryable
    provider, _ = _claude(make_cfg, [(_director_output(), "refusal")])
    with pytest.raises(ProviderError) as exc:
        provider.call(provider.build_request({}, fmt="story", scene_count=4, target_seconds=40, cinematic_allowed=0))
    assert exc.value.kind == "refused"


def test_claude_requires_explicit_api_key_and_pins_base_url(make_cfg, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://interactive-session-proxy.invalid")
    ok, why = ClaudeProvider(make_cfg()).available()
    assert not ok and "ANTHROPIC_API_KEY" in why
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-0000000000")
    client = ClaudeProvider(make_cfg()).client()
    assert str(client.base_url).startswith("https://api.anthropic.com")


def test_cinematic_scenes_cannot_carry_code(make_cfg):
    out = _director_output()
    out["scenes"][1].update(render_engine="cinematic", cinematic_prompt="a server room", intent="api_flow")
    board = sb.from_director(sb.DirectorOutput.model_validate(out), topic=TOPIC, sources=[], fmt="story", target=40, director={})
    from video_mcp.providers.claude_provider import grounding_problems
    problems = grounding_problems(board, json.dumps(TOPIC), cinematic_allowed=2)
    assert any("not allowed for api_flow" in p for p in problems)


# ---------- director fallbacks ----------

def test_claude_unavailable_falls_back_to_local_script(make_cfg, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("video_mcp.providers.script_providers.OllamaProvider.available", lambda self: (False, "not running"))
    decisions = []
    board, report, usages = director.create_storyboard(TOPIC, make_cfg(story_points=2), mode="claude", video_id="v", seed="s",
                                                       claude=ClaudeProvider(make_cfg()), decisions=decisions)
    assert board.director["script_provider"] == "template" and not usages
    assert [d["provider"] for d in decisions if not d.get("used", True)] == ["claude", "ollama"]


def test_template_writer_never_invents_numbers():
    topic = {"kind": "roundup", "theme": "MCP servers that give your AI superpowers", "series": "SERVERS",
             "repos": [{"full_name": f"o/tool-{i}", "owner": "o", "name": f"tool-{i}", "description": f"Tool {i} connects agents to databases.",
                        "stars": 1000 * i, "language": "Python", "topics": ["mcp"], "url": f"https://github.com/o/tool-{i}", "readme_excerpt": ""} for i in (1, 2, 3)]}
    from video_mcp import settings
    plan = TemplateProvider(settings.load()).write_plan(topic, 3).plan
    text = " ".join(s.narration for s in plan.scenes)
    assert "1000" not in text and "Number 2: tool 2." in text and plan.repos[2].stars == 3000
    assert engine.unsupported_numbers(text, json.dumps(topic)) == []


# ---------- Higgsfield adapter (fake SDK) ----------

class FakeSDK:
    def __init__(self):
        self.submitted = []

    def submit(self, application, arguments):
        self.submitted.append((application, arguments))
        return N(request_id="req-123")

    def status(self, rid):
        return type("Completed", (), {})()

    def result(self, rid):
        return {"video": {"url": "https://cdn.example.com/out/clip.mp4"}, "meta": {}}


def test_higgsfield_adapter_translates_and_validates(make_cfg):
    cfg = make_cfg(cinematic={"enabled": True, "application": "acct/seedance/v1/text-to-video", "model_label": "seedance1_5",
                              "usd_per_second_upper_bound": .05})
    sdk = FakeSDK()
    hf = HiggsfieldProvider(cfg, sdk=sdk)
    assert hf.available()[0]
    req = CinematicRequest("scene_002", "A calm server room at dawn", 4, negative_guidance=["text"])
    assert hf.estimate_cost(req).usd == .2
    rid = hf.submit(req, "key")
    app, args = sdk.submitted[0]
    assert rid == "req-123" and app == "acct/seedance/v1/text-to-video"
    assert args["duration"] == 4 and args["aspect_ratio"] == "9:16" and args["generate_audio"] is False and "Avoid: text" in args["prompt"]
    assert hf.get_status(rid) == "completed" and hf.fetch_result(rid)["video_url"].endswith("clip.mp4")
    with pytest.raises(ProviderError, match="duration"):
        hf.submit(CinematicRequest("s", "p", 5), "k")     # seedance 1.5 allows 4, 8, 12


def test_higgsfield_needs_explicit_configuration_and_never_guesses_cost(make_cfg):
    assert "enabled" in HiggsfieldProvider(make_cfg(cinematic={"enabled": False, "provider": "higgsfield"})).available()[1]
    assert "application" in HiggsfieldProvider(make_cfg(cinematic={"enabled": True}), sdk=FakeSDK()).available()[1]
    assert HiggsfieldProvider(make_cfg(cinematic={"enabled": True}), sdk=FakeSDK()).estimate_cost(CinematicRequest("s", "p", 4)).usd is None
    assert _find_video_url({"jobs": [{"results": {"raw": {"url": "https://x.y/v.mp4"}}}]}) == "https://x.y/v.mp4"


def test_downloads_reject_private_hosts(tmp_path):
    from video_mcp.security import UnsafeURL
    with pytest.raises(UnsafeURL):
        AssetManager.download("https://127.0.0.1/clip.mp4", tmp_path / "x.mp4")
    with pytest.raises(UnsafeURL):
        AssetManager.download("http://cdn.example.com/clip.mp4", tmp_path / "x.mp4")


def test_cache_key_is_stable_and_sensitive():
    base = dict(provider="higgsfield", model="m", prompt="p", params={"d": 4}, reference_hashes=["b", "a"], seed=1, config={})
    assert cache_key(**base) == cache_key(**{**base, "reference_hashes": ["a", "b"]})
    assert cache_key(**base) != cache_key(**{**base, "prompt": "p2"}) != cache_key(**{**base, "seed": 2})


def test_probe_rejects_corrupt_media(tmp_path):
    bad = tmp_path / "bad.mp4"
    bad.write_bytes(b"\x00" * 2048)
    with pytest.raises(ValueError):
        probe_video(bad)


# ---------- cinematic stage in the pipeline (mock provider) ----------

def _hybrid_board():
    scene = lambda i, **kw: {"id": f"scene_{i:03d}", "narration": f"Scene {i} narration about the future of coding.", "heading": "Future of coding",
                             "role": "hook" if i == 1 else "outro" if i == 3 else "body", **kw}
    spec = {"prompt": "Slow dolly across a quiet studio at night, warm practical lights, room for typography", "duration_seconds": 4}
    return sb.Storyboard(title="Future", scenes=[scene(1, render_engine="cinematic", cinematic=spec), scene(2), scene(3)],
                         creative_direction={"theme": "cinematic-dark"})


def _pipe(tmp_path, make_cfg, budget, provider=None, cinematic=None):
    cfg = make_cfg(budget=budget, cinematic={"enabled": True, "provider": "mock", "usd_per_second_upper_bound": .05, "poll_interval_seconds": 0,
                                             **(cinematic or {})})
    root = tmp_path / "root"
    (root / "public").mkdir(parents=True)
    job = tmp_path / "data" / "jobs" / "abcdef123456"
    job.mkdir(parents=True)
    (job / "status.json").write_text(json.dumps({"state": "running", "phase": "PLANNING"}))
    p = pipeline_mod.Pipeline("abcdef123456", root=root, data=tmp_path / "data", cfg=cfg,
                              cinematic_provider=provider or MockCinematicProvider(cfg, tmp_path / "mock"))
    return p


needs_ffmpeg = pytest.mark.skipif(not have("ffmpeg"), reason="ffmpeg missing")


@needs_ffmpeg
def test_cinematic_generated_once_then_served_from_cache(tmp_path, make_cfg):
    budget = {**PAID, "approval_policy": "auto_within_budget"}
    p = _pipe(tmp_path, make_cfg, budget)
    board = p.generate_assets(_hybrid_board(), "hybrid")
    assert board.scenes[0].layout == "hookBold" and board.scenes[0].assets[0].provenance["cached"] is False   # bold type over footage
    assert p.costs.spent_for_job("abcdef123456") == .2
    # A second job with the identical request reuses the cached asset and spends nothing.
    p2 = _pipe(tmp_path / "second", make_cfg, budget)
    p2.assets = p.assets
    board2 = p2.generate_assets(_hybrid_board(), "hybrid")
    assert board2.scenes[0].assets[0].provenance["cached"] is True and p2.costs.spent_for_job("abcdef123456") == 0


@needs_ffmpeg
def test_missing_approval_falls_back_without_spending(tmp_path, make_cfg):
    p = _pipe(tmp_path, make_cfg, PAID)          # explicit policy, no approval given
    board = p.generate_assets(_hybrid_board(), "hybrid")
    assert board.scenes[0].render_engine == "remotion" and board.scenes[0].qa.status == "fallback"
    assert p.costs.spent_for_job("abcdef123456") == 0
    assert json.loads((p.folder / "approvals.json").read_text())["pending"]


def test_missing_approval_can_pause_instead(tmp_path, make_cfg):
    p = _pipe(tmp_path, make_cfg, {**PAID, "on_missing_approval": "pause"})
    with pytest.raises(pipeline_mod.Paused):
        p.generate_assets(_hybrid_board(), "hybrid")


def test_budget_exhausted_uses_remotion_fallback(tmp_path, make_cfg):
    p = _pipe(tmp_path, make_cfg, {**PAID, "approval_policy": "auto_within_budget", "max_usd_per_video": .1})
    board = p.generate_assets(_hybrid_board(), "hybrid")
    assert board.scenes[0].render_engine == "remotion" and "Per-video cap" in board.scenes[0].qa.issues[0]


def test_unknown_submit_outcome_is_never_resubmitted(tmp_path, make_cfg):
    budget = {**PAID, "approval_policy": "auto_within_budget"}
    cfg = make_cfg(budget=budget, cinematic={"enabled": True, "provider": "mock", "usd_per_second_upper_bound": .05})
    flaky = MockCinematicProvider(cfg, tmp_path / "mock", fail="submit_timeout")
    p = _pipe(tmp_path, make_cfg, budget, provider=flaky)
    board = p.generate_assets(_hybrid_board(), "hybrid")
    assert board.scenes[0].qa.status == "fallback" and p.costs.spent_for_job("abcdef123456") == .2   # possibly charged: kept
    calls = []
    healthy = MockCinematicProvider(cfg, tmp_path / "mock")
    healthy.submit = lambda *a, **k: calls.append(a) or "x"
    p2 = pipeline_mod.Pipeline("abcdef123456", root=p.root, data=p.data, cfg=cfg, cinematic_provider=healthy)
    p2.generate_assets(_hybrid_board(), "hybrid")
    assert calls == []


def test_crash_between_submit_and_record_is_reconciled_not_resubmitted(tmp_path, make_cfg):
    budget = {**PAID, "approval_policy": "auto_within_budget"}
    p = _pipe(tmp_path, make_cfg, budget)
    (p.folder / "generation_journal.json").write_text(json.dumps({"scene_001": {"state": "submitting", "reservation": {"id": "res_x"}}}))
    p.cinematic_provider().submit = lambda *a, **k: pytest.fail("must not resubmit")
    board = p.generate_assets(_hybrid_board(), "hybrid")
    assert "unknown" in board.scenes[0].qa.issues[0]


@needs_ffmpeg
def test_corrupt_provider_output_falls_back(tmp_path, make_cfg):
    budget = {**PAID, "approval_policy": "auto_within_budget"}
    cfg = make_cfg(budget=budget, cinematic={"enabled": True, "provider": "mock", "usd_per_second_upper_bound": .05})
    p = _pipe(tmp_path, make_cfg, budget, provider=MockCinematicProvider(cfg, tmp_path / "mock", fail="corrupt"))
    board = p.generate_assets(_hybrid_board(), "hybrid")
    assert board.scenes[0].render_engine == "remotion" and "generation failed" in board.scenes[0].qa.issues[0]


def test_local_and_claude_modes_never_generate_footage(tmp_path, make_cfg):
    p = _pipe(tmp_path, make_cfg, {**PAID, "approval_policy": "auto_within_budget"})
    p.cinematic_provider().submit = lambda *a, **k: pytest.fail("no paid generation outside hybrid")
    for mode in ("local", "claude"):
        assert p.generate_assets(_hybrid_board(), mode).scenes[0].render_engine == "remotion"


def test_preflight_downgrades_claude_without_authorization(tmp_path, make_cfg, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-0000000000")
    p = _pipe(tmp_path, make_cfg, {"allow_paid_generation": False})
    assert p.preflight_claude("claude") == "local"
    p = _pipe(tmp_path / "b", make_cfg, PAID)
    assert p.preflight_claude("claude") == "local"            # explicit policy, no job approval
    p.costs.approve(p.folder, None, .9)
    assert p.preflight_claude("claude") == "claude"


def test_supplied_storyboard_cannot_point_media_outside_public(tmp_path, make_cfg):
    p = _pipe(tmp_path, make_cfg, PAID)
    (p.root / "public" / "jobs" / "abcdef123456").mkdir(parents=True)
    ok = p.root / "public" / "jobs" / "abcdef123456" / "clip.mp4"
    ok.write_bytes(b"x")
    assert p._safe_media("jobs/abcdef123456/clip.mp4")
    assert not p._safe_media("../../etc/passwd") and not p._safe_media("jobs/missing.mp4")
    board = _hybrid_board()
    board.scenes[0].cinematic.reference_images = ["https://cdn.example.com/ref.png", "http://169.254.169.254/x", "file:///etc/passwd"]
    assert p.cinematic_request(board.scenes[0]).reference_images == ["https://cdn.example.com/ref.png"]
