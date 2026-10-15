import asyncio
import json
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from video_mcp import engine


def test_plan_limits():
    raw = json.loads((engine.ROOT / "examples/first-reel.json").read_text())
    assert len(engine.Plan.model_validate(raw).scenes) == 4
    raw["scenes"][0]["points"] = ["x" * 66]
    with pytest.raises(ValidationError):
        engine.Plan.model_validate(raw)


def test_emphasis_and_stat_must_come_from_narration():
    scene = engine.Scene(heading="h", narration="It is over 8,743 lines long.", caption="x", emphasis="lines", stat="8,743")
    assert (scene.emphasis, scene.stat) == ("lines", "8,743")
    scene = engine.Scene(heading="h", narration="It is very long.", caption="x", emphasis="huge", stat="9,999")
    assert (scene.emphasis, scene.stat) == ("", "")


def test_auto_style_rotates_through_configured_styles(monkeypatch):
    plan = engine.Plan.model_validate_json((engine.ROOT / "examples/first-reel.json").read_text())
    assert engine.resolve_style(plan) in engine.config()["styles"]
    plan.style = "kinetic"
    assert engine.resolve_style(plan) == "kinetic"


def test_job_path_cannot_escape():
    for value in ["../../etc", "/tmp/test", "", "A" * 12]:
        with pytest.raises(ValueError):
            engine.job_path(value)


def test_widget_sounds_are_non_silent_and_match_scene_duration(tmp_path):
    import soundfile as sf

    from video_mcp import audio
    path = tmp_path / "widget.wav"
    audio.scene_sfx(path, 2.0, 1, "repo", 1, False)
    audio, sample_rate = sf.read(path)
    assert sample_rate == 24000
    assert len(audio) == 48000
    assert 0.03 < abs(audio).max() < 0.95


def test_requires_english_copy_and_uses_exact_spoken_caption():
    raw = json.loads((engine.ROOT / "examples/first-reel.json").read_text())
    raw["title"] = "A local video studio"
    for scene in raw["scenes"]:
        scene["heading"] = "A better video workflow"
        scene["narration"] = "A local model writes a short script for each video."
        scene["caption"] = "This caption is replaced by the spoken words."
        scene["points"] = ["Local script", "Clear narration"]
    plan = engine.Plan.model_validate(raw)
    assert all(scene.caption == scene.narration for scene in plan.scenes)

    raw = json.loads((engine.ROOT / "examples/first-reel.json").read_text())
    raw["scenes"][0]["narration"] = "यह English-only नहीं है।"
    with pytest.raises(ValidationError):
        engine.Plan.model_validate(raw)


def test_plan_supports_detailed_english_repository_scenes():
    plan = engine.Plan(
        title="Agent Reach: The Internet Layer for AI Agents",
        source_urls=["https://github.com/Panniantong/Agent-Reach"],
        scenes=[
            {
                "heading": "One command, many sources",
                "narration": "Agent Reach helps an AI agent search the web, read video transcripts, and inspect public repositories.",
                "caption": "A caption that will be replaced.",
                "points": ["Web", "Video", "Code"],
            },
            {
                "heading": "The layer behind the tools",
                "narration": "It selects and checks upstream tools, while the agent calls those tools directly to read and search.",
                "caption": "A caption that will be replaced.",
                "points": ["Choose", "Install", "Diagnose"],
            },
        ],
    )
    assert len(plan.scenes) == 2
    assert all(scene.caption == scene.narration for scene in plan.scenes)

    raw = plan.model_dump()
    raw["scenes"][0]["narration"] = "यह English नहीं है।"
    with pytest.raises(ValidationError):
        engine.Plan.model_validate(raw)


def test_discovery_handles_feed_failure_and_skips_used_topics(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "DATA", tmp_path)
    monkeypatch.setattr(engine, "history_ids", lambda: set())
    monkeypatch.setattr(engine, "used_repos", lambda: set())
    monkeypatch.setattr(engine, "config", lambda: {"feeds":["good", "bad"], "keywords":["AI"], "max_age_days":7})
    body = "AI details. " * 80
    import email.utils
    xml = f'<rss><channel><item><title>AI release</title><description>{body}</description><link>https://example.com/a</link><pubDate>{email.utils.formatdate(usegmt=True)}</pubDate></item><item><title>Availability report</title><link>https://example.com/b</link><pubDate>{email.utils.formatdate(usegmt=True)}</pubDate></item></channel></rss>'
    class Response:
        content = xml.encode()
        def raise_for_status(self): pass
    class Client:
        def __init__(self, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, url, **kwargs):
            if url == "bad": raise RuntimeError("Offline")
            return Response()
    monkeypatch.setattr(engine.sources.httpx, "Client", Client)
    result = engine.discover()
    assert len(result["topics"]) == 1
    assert len(result["errors"]) == 1
    monkeypatch.setattr(engine, "history_ids", lambda: {result["topics"][0]["id"]})
    assert not engine.discover()["topics"]


def test_real_mcp_handshake_and_health():
    async def check():
        params = StdioServerParameters(command=sys.executable, args=["-m", "video_mcp.server"], cwd=str(engine.ROOT))
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                listing = await session.list_tools()
                assert {"create_video", "discover_topics", "run_autopilot_once", "job_status"} <= {t.name for t in listing.tools}
                result = await session.call_tool("health_check", {})
                assert not result.isError
                assert '"api_keys_required": false' in result.content[0].text
    asyncio.run(check())


def _roundup_topic():
    repos = [{"full_name": f"o/tool-{i}", "owner": "o", "name": f"tool-{i}", "description": "d", "stars": 100 * i,
              "language": "Python", "topics": [], "url": f"https://github.com/o/tool-{i}", "readme_excerpt": ""} for i in (1, 2, 3)]
    return {"kind": "roundup", "repos": repos, "theme": "t", "series": "REPOS"}


def _scene(text):
    return {"heading": "h", "narration": text, "caption": text}


def test_shape_plan_enforces_structure_and_real_repo_data():
    topic = _roundup_topic()
    scenes = [_scene("Hook line.")] + [_scene(f"Tool {i} does a thing.") for i in (1, 2, 3)] + [_scene("Save this.")]
    with pytest.raises(ValueError, match="emphasis"):
        engine.shape_plan(engine.Plan(title="t", scenes=scenes, series="plugins!"), topic, 3)
    plan = engine.shape_plan(engine.Plan(title="t", scenes=scenes, series="plugins!"), topic, 3, strict=False)
    assert all(s.emphasis for s in plan.scenes) and all(s.points for s in plan.scenes if s.item)
    assert [s.visual for s in plan.scenes] == ["hook", "repo", "repo", "repo", "outro"]
    assert [s.item for s in plan.scenes] == [0, 1, 2, 3, 0]
    assert [r.stars for r in plan.repos] == [100, 200, 300] and plan.series == "PLUGINS"
    with pytest.raises(ValueError):
        engine.shape_plan(engine.Plan(title="t", scenes=scenes[:4]), topic, 3, strict=False)
    scenes[2] = _scene("Something unrelated.")
    with pytest.raises(ValueError):
        engine.shape_plan(engine.Plan(title="t", scenes=scenes), topic, 3)
    plan = engine.shape_plan(engine.Plan(title="t", scenes=scenes), topic, 3, strict=False)
    assert plan.scenes[2].narration.startswith("Number 2: tool 2.")


def test_mouth_envelope_and_word_timings():
    import numpy as np
    from types import SimpleNamespace as N
    from video_mcp import audio
    env = audio.mouth_envelope(np.r_[np.zeros(24000), np.ones(24000) * .3].astype("float32"), 30)
    assert len(env) == 60 and env[5] == 0 and env[45] == 1
    tok = lambda t, s, e: N(text=t, start_ts=s, end_ts=e)
    results = [N(audio=np.zeros(24000), tokens=[tok("Hi", 0, .2), tok("!", .2, .3)]), N(audio=np.zeros(100), tokens=[tok("Go", .1, .4)])]
    assert audio.word_timings(results) == [{"w": "Hi!", "s": 0, "e": .2}, {"w": "Go", "s": 1.1, "e": 1.4}]


def test_unsupported_numbers_are_flagged_and_removed():
    assert engine.unsupported_numbers("It has 152 cards and 0 previews and 4 repos.", '{"d": "152 shot cards, 209 previews"}') == []
    assert engine.unsupported_numbers("It saves 90% and 3,500 hours.", '{"d": "saves 3500 hours"}') == ["90"]
    topic = _roundup_topic()
    scenes = [_scene("Hook line.")] + [_scene(f"Tool {i} does a thing. It has 999 users.") for i in (1, 2, 3)] + [_scene("Save this.")]
    plan = engine.shape_plan(engine.Plan(title="t", scenes=scenes), topic, 3, strict=False)
    assert plan.scenes[1].narration == "Tool 1 does a thing."


def test_beats_split_on_punctuation_and_cap_length():
    from video_mcp import variety
    words = [{"w": w, "s": i * .4, "e": i * .4 + .35} for i, w in enumerate("One two three four, five six seven eight nine ten eleven twelve.".split())]
    beats = variety.split_beats(words, 5.0)
    assert beats[0]["s"] == 0 and beats[-1]["e"] == 5.0
    assert all(b["e"] - b["s"] <= 3.6 for b in beats) and len(beats) >= 2


def test_layouts_vary_and_never_repeat_back_to_back(tmp_path):
    from video_mcp import variety
    def scene(visual, item, text):
        words = [{"w": w, "s": i * .4, "e": i * .4 + .35} for i, w in enumerate(text.split())]
        return {"visual": visual, "item": item, "words": words, "beats": variety.split_beats(words, len(words) * .4 + .3),
                "emphasis": "fast", "heading": "h", "label": f"tool-{item}", "stat": ""}
    line = "This tool is fast, it ships 300 commands. You install it once, then forget it. It just works every day."
    scenes = [scene("hook", 0, line)] + [scene("repo", i, line) for i in (1, 2, 3)] + [scene("outro", 0, line)]
    for s in scenes:
        s["_roundup"] = True
    order = variety.plan_layouts(scenes, variety.choose_variant("abc", tmp_path / "v.json"))
    assert all(a != b for a, b in zip(order, order[1:]))
    assert order[-1] == "loop" and len(set(order)) >= 6
    a, b = variety.choose_variant("job1", tmp_path / "v.json"), variety.choose_variant("job2", tmp_path / "v.json")
    assert a != b and a == variety.choose_variant("job1", tmp_path / "v.json")


def test_visemes_from_phonemes_hold_closures():
    import numpy as np
    from types import SimpleNamespace as N
    from video_mcp import audio
    tok = lambda t, p, s, e: N(text=t, phonemes=p, start_ts=s, end_ts=e)
    cues = audio.visemes([N(audio=np.zeros(48000), tokens=[tok("map", "mˈæp", .2, .7), tok("food", "fˈud", .8, 1.3)])], 30)
    shapes = [c[1] for c in cues]
    assert "A" in shapes and "D" in shapes and "G" in shapes and "F" in shapes
    assert all(b[0] - a[0] >= 2 for a, b in zip(cues, cues[1:]))
