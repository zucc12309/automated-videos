"""V2.2: hooks, CTA engine + resources, visual director / character staging, premium QA, typography, vibe_coding format."""
import json
import re
from pathlib import Path

import pytest

from video_mcp import settings, sources
from video_mcp.creative import cta, director, hooks, visual_director
from video_mcp.quality import premium_checks

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------- hooks
def test_hook_scoring_disqualifies_hype_and_unsupported_numbers():
    allowed = {"4"}
    assert hooks.score("This 10x hack is insane", allowed)["score"] == 0
    assert hooks.score("37 repos for Claude Code", allowed)["score"] == 0          # 37 is not in the source data
    good = hooks.score("4 GitHub repos that make Claude Code better.", allowed)
    assert good["score"] > 0 and good["parts"]["credibility"] == 1


def test_hook_candidates_are_three_and_choice_is_the_best_scored():
    topic = {"title": "4 repos that fix Claude Code's gaps", "theme": "Claude Code repos"}
    text, scored = hooks.choose(topic, "roundup", 4, json.dumps(topic))
    assert len(scored) == 3 and text == scored[0]["text"]
    assert scored == sorted(scored, key=lambda x: (-x["score"], len(x["text"])))
    assert "Claude Code" in text and all(s["parts"]["credibility"] == 1 for s in scored)


# ---------------------------------------------------------------- CTA engine
@pytest.mark.parametrize("fmt,topic,keyword", [
    ("roundup", {"title": "4 repos"}, "LINK"),
    ("vibe_coding", {"title": "Scope your UI prompts"}, "PROMPT"),
    ("story", {"title": "How MCP connects agents to tools"}, "GUIDE"),
])
def test_cta_keyword_follows_content_type(fmt, topic, keyword):
    plan = cta.plan(fmt, topic, 4)
    assert plan["keyword"] == keyword and keyword in plan["narration"]


def test_cta_never_promises_a_dm_without_a_delivery_integration():
    templates = json.loads((ROOT / "brand/cta_templates.json").read_text())
    assert templates["fulfillment"]["dm_delivery_enabled"] is False
    plan = cta.plan("roundup", {"title": "x"}, 4, dm_enabled=True)       # config flag alone is not enough
    assert plan["dm_promised"] is False and not premium_checks.DM_PROMISE.search(plan["narration"] + " " + plan["secondary"])
    assert plan["fulfillment"].startswith("manual")


def test_cta_resources_are_written_for_manual_sending(tmp_path, make_cfg):
    tip = next(t for t in sources.vibe_topics(set()) if t["id"] == "vibe-scope-ui")
    cfg = make_cfg()
    board = director.finish(director.vibe_storyboard(tip, cfg, video_id="abcdef123456", seed="t"), tip, cfg)
    manifest = cta.write_resources(tmp_path, board, tip)
    out = tmp_path / "resources"
    for name in ("guide.md", "prompt.md", "dm_message.txt", "resource_manifest.json"):
        assert (out / name).exists(), name
    assert manifest["keyword"] == "PROMPT" and manifest["dm_promised_in_video"] is False
    assert tip["better"][0] in (out / "prompt.md").read_text()


# ---------------------------------------------------------------- vibe_coding format
def test_vibe_library_topics_and_storyboard(make_cfg):
    tips = sources.vibe_topics(set())
    assert len(tips) >= 4 and all(t["kind"] == "vibe_coding" for t in tips)
    assert not any(t["id"] == tips[0]["id"] for t in sources.vibe_topics({tips[0]["id"]}))
    cfg = make_cfg()
    board = director.finish(director.vibe_storyboard(tips[0], cfg, video_id="abcdef123456", seed="t"), tips[0], cfg)
    assert board.format == "vibe_coding" and board.scenes[-1].cta["keyword"] == "PROMPT"
    compare = next(s for s in board.scenes if s.visual.prompt_after)
    assert compare.visual.prompt_before == tips[0]["weak"][:len(compare.visual.prompt_before)]
    assert len(board.hook_candidates) >= 3 and all("score" in h for h in board.hook_candidates)
    assert board.creative_direction.theme == "fieldnotes-premium"


def test_v22_defaults_and_brand_profile(cfg_dict):
    cfg = settings.from_dict(cfg_dict)
    assert cfg.production.theme == "fieldnotes-premium" and cfg.production.style == "premium"
    assert cfg.brand_profile.public_character_name is None and cfg.brand_profile.cta_dm_delivery_enabled is False
    assert "vibe_coding" in cfg_dict.get("formats", [])
    legacy = settings.from_dict({"model": "x"})
    assert legacy.production.style == "premium" and legacy.brand_profile.wordmark == "FIELDNOTES"


# ---------------------------------------------------------------- visual director + character
def _scene(sid, role, layouts, item=0, stars=0, seconds=4.0):
    n = len(layouts)
    beats = [{"s": i * seconds / n, "e": (i + 1) * seconds / n, "w": [0, 0], "layout": l, "text": "t"} for i, l in enumerate(layouts)]
    return {"id": sid, "role": role, "item": item, "_stars": stars, "frames": int(seconds * 30), "beats": beats}


def _video():
    return [_scene("scene_001", "hook", ["hookBold"]), _scene("scene_002", "item", ["repoCard", "terminal"], item=1, stars=500),
            _scene("scene_003", "item", ["repoCard", "codeBlock"], item=2, stars=9000), _scene("scene_004", "body", ["cinematic"]),
            _scene("scene_005", "outro", ["outroCTA", "loop"])]


def test_visual_director_signatures_and_transitions():
    scenes = _video()
    report = visual_director.direct(scenes, character_mode="on")
    beats = [b for s in scenes for b in s["beats"]]
    first = beats[0]
    assert first["transition"] == "cut" and first["character"]["scale"] == "closeup"
    assert scenes[1]["beats"][1]["transition"] == "expand"                 # repo card expands into its terminal
    assert scenes[2]["beats"][0]["transition"] == "push"                   # numbered list progression
    cta_beat = scenes[4]["beats"][0]["character"]
    assert cta_beat["state"] == "pointing" and cta_beat.get("wink")
    assert scenes[3]["beats"][0]["character"]["scale"] == "hidden"         # footage gets the full frame
    surprised = [b for b in beats if b["character"]["state"] == "surprised"]
    assert len(surprised) == 1 and report["reveal_scene"] == "scene_003"   # most-starred item
    assert all(b["direction"]["transition"] and b["direction"]["character"] for b in beats)


def test_visual_director_merges_too_short_beats_and_respects_character_off():
    scenes = [_scene("scene_001", "hook", ["hookBold"]), _scene("scene_002", "body", ["heroWord", "steps", "quote"], seconds=3.0)]
    visual_director.direct(scenes, character_mode="off")
    assert len(scenes[1]["beats"]) < 3
    assert all(b["character"]["scale"] == "hidden" for s in scenes for b in s["beats"])


# ---------------------------------------------------------------- premium QA
def _props():
    scenes = _video()
    visual_director.direct(scenes, character_mode="on")
    t = 0
    for s in scenes:
        s.update(heading="4 repos for Claude Code" if s["role"] == "hook" else "Heading", points=["a"], narration="Text.",
                 **({"from": t}))
        t += s["frames"]
    scenes[-1].update(narration="Want all 4 repos? Comment LINK for the list.", cta={"keyword": "LINK", "secondary": "Get the full repo list"})
    return {"fps": 30, "style": "premium", "scenes": scenes, "durationInFrames": t}


def test_premium_checks_pass_on_a_directed_video():
    rows = premium_checks.checks(_props())
    failed = [r for r in rows if not r["passed"]]
    assert not failed, failed
    names = {r["check"] for r in rows}
    assert {"hook_frame0", "signature_entrance", "signature_cta", "one_reveal_reaction", "cta_keyword", "cta_truthful", "min_hold"} <= names


def test_premium_checks_catch_dm_promises_missing_keyword_and_unapproved_name():
    props = _props()
    props["scenes"][-1]["narration"] = "Comment below and I'll send you the list."
    props["scenes"][1]["heading"] = "Mochi explains"
    bad = {r["check"] for r in premium_checks.checks(props) if not r["passed"]}
    assert {"cta_truthful", "cta_keyword", "no_unapproved_name"} <= bad


def test_premium_typography_meets_mobile_minimums():
    for _, rows in premium_checks.PREMIUM_TEXT.items():
        for field, _, px, cls in rows:
            assert px >= premium_checks.MIN[cls], (field, px, cls)
    tokens = json.loads((ROOT / "brand/tokens.json").read_text())["type"]
    assert tokens["masthead"] >= 32 and tokens["minMeta"] >= 32 and tokens["minBody"] >= 40 and tokens["headline"] >= 48
    for name in ("Objects.tsx", "Frame.tsx"):
        sizes = [int(x) for x in re.findall(r"fontSize: (\d+)\b", (ROOT / "src/premium" / name).read_text())]
        assert min(sizes, default=32) >= 32, (name, min(sizes))


def test_character_identity_keeps_public_name_configurable():
    identity = json.loads((ROOT / "brand/character/identity.json").read_text())
    assert identity["public_name"] is None
    states = set(identity["states"])
    assert {"idle", "speaking", "thinking", "pointing", "typing", "explaining", "surprised", "celebrating", "warning", "confused",
            "presenting", "exiting"} <= states
    for f in (ROOT / "src/premium").glob("*.tsx"):
        assert identity["provisional_name"] not in f.read_text(), f.name


def test_storyboard_requested_celebration_replaces_the_automatic_reveal():
    scenes = _video()
    scenes[1]["character_action"] = "celebrating"
    visual_director.direct(scenes, character_mode="on")
    big = [b["character"]["state"] for s in scenes for b in s["beats"] if b["character"]["state"] in ("surprised", "celebrating")]
    assert big == ["celebrating"]


def _route(scene, text="Most people type something vague here and hope."):
    from video_mcp.creative import semantic_router as sr
    beat = {"s": 0, "e": 4, "text": text}
    ctx = sr.beat_context({"role": "body", "points": [], **scene}, beat, 0, character=True)
    return sr.choose(ctx, [], {}, "seed", 0, "fieldnotes-premium")[0]


def test_router_keeps_authored_vibe_layouts_when_their_data_is_present():
    weak = ["make the dashboard look better"]
    assert _route({"intent": "warning", "layoutHint": "terminal", "points": ["Guesswork"],
                   "visualData": {"code": [f"> {weak[0]}"], "code_language": "prompt"}}) == "terminal"
    assert _route({"intent": "comparison", "layoutHint": "splitCompare",
                   "visualData": {"prompt_before": weak, "prompt_after": ["Only edit Dashboard.tsx", "Use the tokens"]}}) == "splitCompare"


def test_loop_tail_cuts_back_to_the_hook():
    scenes = _video()
    visual_director.direct(scenes, character_mode="on")
    assert scenes[-1]["beats"][-1]["transition"] == "cut"


# ---------------------------------------------------------------- reference audio profile
def test_audio_profile_has_reference_measurements_and_targets():
    from video_mcp import audio_profile
    p = audio_profile.profile()
    m = p["measured"]
    assert -15 < m["integrated_lufs"] < -13 and m["f0_median"] and m["bed_minus_speech_db"] < -15
    espeak = p["targets"]["voice"]["espeak"]
    assert espeak["variant"].startswith("en-us") and espeak["pitch"].endswith("%")
    assert p["targets"]["voice"]["kokoro"]["voice"] == "am_adam"


def test_match_eq_moves_band_balance_toward_target_and_is_clamped():
    import numpy as np
    from video_mcp import audio_profile
    rng = np.random.default_rng(0)
    x = rng.standard_normal(16000 * 2).astype(np.float32)
    target = {"low": -4.0, "mid": -3.0, "presence": -12.0, "air": -17.0}
    chain, info = audio_profile.match_eq(x, 16000, target)
    assert all(abs(g) <= audio_profile.EQ_LIMIT_DB for g in info["gains_db"].values())
    assert info["gains_db"]["air"] < 0 and info["gains_db"]["low"] > 0       # white noise is air-heavy, low-light
    assert "equalizer" in chain


def test_bed_gain_places_music_under_speech_by_the_reference_margin():
    import numpy as np
    from video_mcp import audio_profile
    t = np.arange(24000 * 2) / 24000
    voice = (.3 * np.sin(2 * np.pi * 150 * t)).astype(np.float32)
    music = (.3 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    gain = audio_profile.bed_gain_db([voice], music, 24000, -22.0)
    assert abs(gain + 22.0) < .5                                               # equal levels -> 22 dB down


def test_warm_pad_bed_is_darker_than_the_lofi_bed(tmp_path):
    import numpy as np
    import soundfile as sf
    from video_mcp import audio as audio_fx
    def high_share(p):          # energy above 1 kHz (hats, plucks) relative to the whole bed
        x, sr = sf.read(p, dtype="float32")
        X = np.abs(np.fft.rfft(x)) ** 2
        f = np.fft.rfftfreq(len(x), 1 / sr)
        return X[f > 1000].sum() / X.sum()
    audio_fx.music_bed(tmp_path / "pad.wav", 8, 92, 1, None, style="warm_pad")
    audio_fx.music_bed(tmp_path / "lofi.wav", 8, 92, 1, None)
    assert high_share(tmp_path / "pad.wav") < high_share(tmp_path / "lofi.wav") / 5


def test_espeak_uses_reference_prosody_when_profile_is_on(monkeypatch, make_cfg):
    import shutil
    import subprocess
    from video_mcp import tts
    calls = []
    def fake_run(cmd, **kw):
        calls.append(cmd)
        raise RuntimeError("stop after the first call")
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/espeak-ng")
    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(RuntimeError):
        tts.espeak_narrate("A scope & a check.", make_cfg(narration={"audio_profile": "reference"}), 30)
    cmd = calls[0]
    assert "-m" in cmd and 'pitch="+' in cmd[-1] and "&amp;" in cmd[-1]
    calls.clear()
    with pytest.raises(RuntimeError):
        tts.espeak_narrate("Plain.", make_cfg(narration={"audio_profile": "off"}), 30)
    assert "-m" not in calls[0]
