"""QA checks, MCP surface, job recovery and (opt-in) an end-to-end local render."""
import asyncio
import json
import os
import subprocess
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from video_mcp import engine
from video_mcp.quality import audio_analysis, frame_analysis, quality_report, video_validation

from conftest import have

needs_ffmpeg = pytest.mark.skipif(not have("ffmpeg"), reason="ffmpeg missing")


def _props(layouts, theme="carbon", items=0, **scene_extra):
    beats = [{"s": i * 2.0, "e": i * 2.0 + 2, "w": [0, 0], "text": "word", "focus": "word", "layout": l, "anchor": "right"} for i, l in enumerate(layouts)]
    scene = {"id": "scene_001", "heading": "A heading", "points": ["one", "two"], "item": items, "words": [{"w": "word", "s": 0, "e": .4}],
             "beats": beats, "from": 0, "frames": 60 * len(layouts), "visualData": {}, **scene_extra}
    return {"fps": 30, "width": 1080, "height": 1920, "durationInFrames": 60 * len(layouts), "variant": {"theme": theme}, "scenes": [scene]}


# ---------- deterministic layout QA ----------

def test_layout_checks_pass_on_clean_props():
    report = frame_analysis.layout_checks(_props(["heroWord", "listStack", "quote"]))
    assert not report["issues"]


def test_layout_checks_flag_overflow_repeats_empty_and_missing_assets():
    props = _props(["listStack", "listStack", "hookStack", "cinematic"], points=["x" * 60, "short"])
    kinds = {i["kind"] for i in frame_analysis.layout_checks(props)["issues"]}
    assert {"overflow", "repetition", "blank", "missing_asset"} <= kinds


def test_theme_contrast_tokens_meet_wcag():
    for name in frame_analysis.themes():
        issues = [i for i in frame_analysis.layout_checks(_props(["heroWord"], theme=name))["issues"] if i["kind"] == "contrast"]
        assert not issues, (name, issues)


def test_repair_plan_targets_only_failing_scenes():
    props = _props(["listStack", "quote"], points=["x" * 60])
    report = {"visual": {"issues": frame_analysis.layout_checks(props)["issues"]}}
    overrides = quality_report.plan_repairs(report, props)
    assert overrides["shorten"] == {"scene_001": {"points": 26}} and overrides["avoid"] == {}
    blank = {"visual": {"issues": [{"kind": "blank", "scene": "scene_001"}]}, "audio": {"checks": [{"check": "true_peak", "passed": False}]}}
    overrides = quality_report.plan_repairs(blank, props)
    assert overrides["avoid"] == {"scene_001": ["listStack"]} and overrides["remaster"]


def test_shorten_cuts_at_word_boundaries():
    assert quality_report.shorten("Ripgrep is a line-oriented search tool for the", 34) == "Ripgrep is a line-oriented search"
    assert quality_report.shorten("Fits fine", 20) == "Fits fine"
    assert len(quality_report.shorten("x" * 60, 26)) == 26


# ---------- technical QA on real media ----------

@pytest.fixture(scope="module")
def clip(tmp_path_factory):
    if not have("ffmpeg"):
        pytest.skip("ffmpeg missing")
    out = tmp_path_factory.mktemp("clip") / "clip.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1080x1920:r=30:d=3", "-f", "lavfi", "-i", "color=black:s=1080x1920:r=30:d=1",
                    "-f", "lavfi", "-i", "sine=f=440:d=4:sample_rate=48000", "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]",
                    "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(out)], check=True)
    return out


@needs_ffmpeg
def test_technical_checks_measure_media(clip):
    report = video_validation.technical(clip, width=1080, height=1920, fps=30, expected_seconds=4)
    by = {c["check"]: c for c in report["checks"]}
    assert by["resolution"]["passed"] and by["frame_rate"]["passed"] and by["audio_present"]["passed"] and by["decode_integrity"]["passed"]
    assert not by["black_frames"]["passed"] and report["black_segments"][0][0] == pytest.approx(3.0, abs=.1)
    assert not report["passed"]
    wrong = video_validation.technical(clip, width=720, height=1280, fps=25, expected_seconds=10)
    assert not {c["check"]: c for c in wrong["checks"]}["resolution"]["passed"]


@needs_ffmpeg
def test_loudness_measurement(clip):
    loud = audio_analysis.loudness(clip)
    assert loud["integrated_lufs"] is not None and loud["true_peak_dbtp"] is not None


# ---------- engine: history, recovery ----------

def _job(tmp_path, ident, **status):
    folder = tmp_path / ident
    folder.mkdir(parents=True)
    (folder / "status.json").write_text(json.dumps({"id": ident, **status}))
    return folder


def test_dry_runs_and_failures_do_not_consume_topics(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "JOBS", tmp_path)
    _job(tmp_path, "aaaaaaaaaaaa", state="completed", topic_id="t1")
    _job(tmp_path, "bbbbbbbbbbbb", state="completed", topic_id="t2", dry_run=True)
    _job(tmp_path, "cccccccccccc", state="failed", topic_id="t3")
    assert engine.history_ids() == {"t1"}


def test_dead_worker_is_marked_resumable_and_resumes(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "JOBS", tmp_path)
    folder = _job(tmp_path, "dddddddddddd", state="running", phase="RENDERING", pid=2 ** 22 + 12345)
    status = engine.status("dddddddddddd")
    assert status["state"] == "failed" and status["resumable"]
    spawned = []
    monkeypatch.setattr(engine, "spawn", lambda ident: spawned.append(ident) or 4242)
    (folder / "checkpoints.json").write_text(json.dumps({"direction": {}, "narration": {}}))
    result = engine.resume_job("dddddddddddd")
    assert result["resumed"] and spawned == ["dddddddddddd"] and result["checkpoints"] == ["direction", "narration"]


def test_start_job_keeps_v1_signature(tmp_path, monkeypatch, example_plan):
    monkeypatch.setattr(engine, "JOBS", tmp_path)
    monkeypatch.setattr(engine, "spawn", lambda ident: 1)
    result = engine.start_job(plan=example_plan)
    request = json.loads((tmp_path / result["id"] / "request.json").read_text())
    assert result["state"] == "queued" and request["mode"] == "local" and request["plan"]["title"] == example_plan.title


# ---------- MCP surface ----------

def test_mcp_tools_preserved_and_extended(example_plan):
    async def check():
        params = StdioServerParameters(command=sys.executable, args=["-m", "video_mcp.server"], cwd=str(engine.ROOT))
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                names = {t.name for t in (await session.list_tools()).tools}
                original = {"health_check", "discover_topics", "create_video", "create_video_from_topic", "run_autopilot_once", "job_status", "list_videos"}
                new = {"preview_storyboard", "estimate_video_cost", "create_hybrid_video", "approve_generation", "review_video", "repair_video",
                       "list_assets", "get_video_report", "cancel_job", "resume_job", "import_motion_clip"}
                assert original | new <= names
                preview = await session.call_tool("preview_storyboard", {"plan": example_plan.model_dump()})
                assert not preview.isError
                data = json.loads(preview.content[0].text)
                assert len(data["scenes"]) == 4 and all(b["layout"] for s in data["scenes"] for b in s["beats"])
                cost = await session.call_tool("estimate_video_cost", {"mode": "local"})
                assert json.loads(cost.content[0].text)["total_upper_bound_usd"] == 0
                bad = await session.call_tool("create_hybrid_video", {"mode": "local"})
                assert bad.isError
    asyncio.run(check())


# ---------- opt-in end-to-end render (slow: ~1-2 min) ----------

@pytest.mark.skipif(os.environ.get("RUN_SLOW") != "1", reason="set RUN_SLOW=1 to render a real video")
def test_end_to_end_local_render(tmp_path, example_plan, make_cfg):
    from video_mcp.orchestration.pipeline import Pipeline
    data = tmp_path / "data"
    folder = data / "jobs" / "eeeeeeeeeeee"
    folder.mkdir(parents=True)
    (folder / "status.json").write_text(json.dumps({"state": "running"}))
    pipe = Pipeline("eeeeeeeeeeee", root=engine.ROOT, data=data, cfg=make_cfg())
    status = pipe.run({"plan": example_plan.model_dump(), "mode": "local"})
    assert status["state"] == "completed" and (folder / "video.mp4").exists() and (folder / "qa" / "contact_sheet.jpg").exists()
    for name in ("plan.json", "props.json", "storyboard.json", "costs.json", "provenance.json", "checks.json", "qa/technical.json"):
        assert (folder / name).exists(), name
    assert json.loads((folder / "costs.json").read_text())["total_external_usd"] == 0
