"""Game reel: spec rules the brief fixes (CTA wording, loop, honesty, layout) and the cut resolver's guard against running past a recording."""
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples" / "game_reel"))
sys.path.insert(0, str(ROOT / "examples" / "series"))
sys.path.insert(0, str(ROOT / "examples" / "devmimo"))

SPEC = json.loads((ROOT / "reels" / "claude-game" / "reel.json").read_text())
LAYOUT = json.loads((ROOT / "src" / "gamereel" / "layout.json").read_text())
norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())


def beat(i):
    return next(b for b in SPEC["beats"] if b["id"] == i)


def test_beats_follow_the_brief():
    assert [b["id"] for b in SPEC["beats"]] == ["hook", "idea", "build", "features", "iteration", "result", "cta"]
    assert beat("hook")["headline"]["lines"] == ["I BUILT THIS GAME", "WITH CLAUDE."]
    assert beat("hook")["segs"][0]["clip"] in SPEC["clips"]          # gameplay first, no title card
    assert beat("result")["headline"]["lines"] == ["BUILT WITH CLAUDE."]
    assert beat("result")["pill"]["text"] == "STILL IN DEVELOPMENT"


def test_cta_is_exact():
    c = beat("cta")
    assert norm(c["cta"]["big"] + c["cta"]["small"]) == norm("COMMENT LINK OR DM ME LINK")
    assert norm("Comment LINK, or DM me LINK") in norm(c["narration"])


def test_reel_loops_back_to_its_opening():
    assert beat("cta")["segs"][-1]["clip"] == beat("hook")["segs"][0]["clip"]
    assert beat("cta")["segs"][-1]["src_end"] == pytest.approx(beat("hook")["segs"][0]["src"])


def test_claims_have_sources_and_narration_stays_honest():
    for k in ("36 puzzles", "5 worlds", "built with Claude", "still in development"):
        assert SPEC["claims"][k]
    text = " ".join(b["narration"] for b in SPEC["beats"]).lower()
    for banned in ("in a day", "hours", "published", "app store", "by itself", "automatically"):
        assert banned not in text


def test_no_private_names_in_committed_reel_files():
    # the actual list is git-ignored (data/game-reel/private_terms.json); these generic shapes must never appear either
    files = [ROOT / "reels" / "claude-game" / f for f in ("reel.json", "caption.md", "prompt.md")] + [ROOT / "src" / "gamereel" / "GameReel.tsx"]
    for f in files:
        t = f.read_text().lower()
        assert "github.com/" not in t and "claude/" not in t, f
    terms = ROOT / SPEC["private_terms_file"]
    if terms.exists():
        for t in json.loads(terms.read_text()):
            for f in files:
                assert t.lower() not in f.read_text().lower(), (t, f.name)


def test_layout_inside_instagram_safe_area():
    s = LAYOUT["safe"]
    regions = [LAYOUT["card"], LAYOUT["headline"], LAYOUT["pill"], LAYOUT["prompt"], LAYOUT["split"]["left"], LAYOUT["split"]["right"],
               LAYOUT["split"]["note"], LAYOUT["mimo"], LAYOUT["handle"],
               [LAYOUT["subtitle"]["x"], LAYOUT["subtitle"]["y"], LAYOUT["subtitle"]["w"], LAYOUT["subtitle"]["max_h"]]]
    for x, y, w, h in regions:
        assert x >= s["left"] and y >= s["top"] and x + w <= s["right"] and y + h <= s["bottom"]
    assert LAYOUT["card"][1] + LAYOUT["card"][3] <= LAYOUT["subtitle"]["y"]


def test_resolver_refuses_cuts_past_a_recording(monkeypatch):
    import build_game_reel as g
    monkeypatch.setattr(g, "clip_seconds", lambda clip: 3.0)
    spec = {"beats": [{"id": "hook", "narration": "a b c", "segs": [{"clip": "hook", "src": 2.0}]}]}
    timed = [{"id": "hook", "kind": "hook", "from": 0, "frames": 60, "words": [{"w": "a", "s": 0, "e": .2}], "lead_s": 0, "speech_s": .2}]
    with pytest.raises(SystemExit, match="past their recordings"):
        g.resolve(spec, timed)
    spec["beats"][0]["segs"][0]["src"] = 0.5
    out = g.resolve(spec, timed)
    assert out[0]["segs"] == [{"clip": "hook", "src": 0.5, "from": 0, "frames": 60, "crop_y": 0}]
