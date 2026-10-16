"""DevMimo intro: storyboard integrity, narration-driven timing, cue placement, palette metric. No rendering, no TTS."""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples" / "devmimo"))

import build_intro  # noqa: E402
import qa  # noqa: E402


def story():
    return json.loads((ROOT / "examples" / "devmimo" / "devmimo_intro_storyboard.json").read_text())


def fake_voice(s, seconds=None):
    out = []
    for i, scene in enumerate(s["scenes"]):
        words = scene["narration"].split()
        dur = seconds[i] if seconds else .32 * len(words)
        step = dur / len(words)
        out.append({"id": scene["id"], "seconds": dur, "words": [{"w": w, "s": k * step, "e": (k + 1) * step} for k, w in enumerate(words)]})
    return out


def test_storyboard_scenes_have_components():
    kinds = {s["kind"] for s in story()["scenes"]}
    src = (ROOT / "src" / "devmimo" / "DevMimoIntro.tsx").read_text()
    for kind in kinds:
        assert f"{kind}:" in src, kind


def test_sfx_cues_point_at_real_words():
    s = story()
    by = {x["id"]: x["narration"].split() for x in s["scenes"]}
    for cue in s["sfx"]:
        assert cue["scene"] in by
        if "word" in cue:
            assert 0 <= cue["word"] < len(by[cue["scene"]]), cue


def test_timeline_fills_target_and_waits_for_voice():
    s = story()
    scenes = build_intro.timeline(s, fake_voice(s))
    total = sum(x["frames"] for x in scenes)
    assert abs(total / build_intro.FPS - build_intro.TARGET_S) < .1
    for x in scenes:
        assert x["frames"] >= (x["lead_s"] + x["speech_s"]) * build_intro.FPS
    assert [x["from"] for x in scenes] == list(np.cumsum([0] + [x["frames"] for x in scenes[:-1]]))


def test_timeline_never_cuts_long_narration():
    s = story()
    scenes = build_intro.timeline(s, fake_voice(s, [7.0] * len(s["scenes"])))
    for x in scenes:
        assert x["frames"] >= (x["lead_s"] + 7.0) * build_intro.FPS - 1


def test_word_anchored_cue_follows_narration():
    s = {"scenes": story()["scenes"][:1], "sfx": []}
    scenes = build_intro.timeline(s, fake_voice(s))
    word = scenes[0]["words"][2]["s"]
    track = build_intro.sfx_track(scenes, [{"scene": "hook", "word": 2, "frame": 0, "sound": "pop", "gain": 1}], 4.0)
    onset = np.argmax(np.abs(track) > 1e-3) / build_intro.RATE
    assert abs(onset - word) < .01


def test_palette_metric_separates_on_and_off_brand():
    on = np.zeros((1, 40, 40, 3), np.uint8)
    on[..., :] = (10, 11, 15)
    on[:, :10] = (142, 162, 255)
    on[:, 10:20] = (239, 239, 234)
    off = np.zeros((1, 40, 40, 3), np.uint8)
    off[..., :] = (255, 122, 26)
    assert qa.palette_share(on) > .95
    assert qa.palette_share(off) < .05


def test_mimo_is_the_brand_character_in_brand_colours():
    s = story()
    assert "identity.json" in s["mascot_note"]
    mimo = (ROOT / "src" / "devmimo" / "Mimo.tsx").read_text()
    theme = (ROOT / "src" / "devmimo" / "theme.ts").read_text()
    assert "ID.palette" in mimo and "tokens.color" in theme
    assert "#ff7a1a" not in theme.lower()


def test_no_paid_calls():
    src = (ROOT / "examples" / "devmimo" / "build_intro.py").read_text()
    for banned in ("anthropic", "higgsfield", "requests.post", "urlopen"):
        assert banned not in src.lower()
