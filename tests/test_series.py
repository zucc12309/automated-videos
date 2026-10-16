"""Series system: numbering, spec validation, subtitles, captions. No rendering, no TTS."""
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples" / "series"))
sys.path.insert(0, str(ROOT / "examples" / "devmimo"))

from video_mcp import series  # noqa: E402

SLUG = "mimo-found-this-on-github"


@pytest.fixture
def root(tmp_path):
    (tmp_path / SLUG).mkdir()
    shutil.copy(ROOT / "series" / SLUG / "series.json", tmp_path / SLUG / "series.json")
    return tmp_path


def fixture_spec():
    return json.loads((ROOT / "tests" / "fixtures" / "series" / "pipeline_test_spec.json").read_text())


def cfg():
    return series.config(SLUG)


def test_episode_format():
    assert [series.fmt(n) for n in (1, 2, 10, 100, 1000)] == ["EP. 001", "EP. 002", "EP. 010", "EP. 100", "EP. 1000"]
    with pytest.raises(series.SeriesError):
        series.fmt(0)


def test_allocation_is_sequential_and_rerender_keeps_number(root):
    a, created_a = series.allocate(SLUG, "https://github.com/a/one", "One", root=root)
    b, _ = series.allocate(SLUG, "b/two", "Two", root=root)
    assert (a["episode"], b["episode"], created_a) == (1, 2, True)
    again, created = series.allocate(SLUG, "github.com/A/One.git", "One (rerender)", root=root)
    assert again["episode"] == 1 and not created
    assert len(series.episodes(SLUG, root)) == 2


def test_next_number_follows_highest_including_overrides(root):
    series.allocate(SLUG, "a/one", "One", override=7, root=root)
    nxt, _ = series.allocate(SLUG, "b/two", "Two", root=root)
    assert nxt["episode"] == 8


def test_override_never_overwrites(root):
    series.allocate(SLUG, "a/one", "One", root=root)
    with pytest.raises(series.SeriesError, match="will not be overwritten"):
        series.allocate(SLUG, "b/two", "Two", override=1, root=root)
    with pytest.raises(series.SeriesError, match="refusing to renumber"):
        series.allocate(SLUG, "a/one", "One", override=5, root=root)
    assert json.loads(series.record_path(SLUG, 1, root).read_text())["repository"] == "a/one"


def test_update_keeps_identity_and_status_order(root):
    series.allocate(SLUG, "a/one", "One", root=root)
    series.update(SLUG, 1, root, status="published")
    rec = series.update(SLUG, 1, root, status="rendered", title="One again")
    assert rec["status"] == "published" and rec["title"] == "One again"
    with pytest.raises(series.SeriesError):
        series.update(SLUG, 1, root, repository="x/y")


def test_fixture_spec_validates():
    assert series.validate(fixture_spec(), cfg()) == []


def test_validation_rejects_unverified_labels_hype_and_stats():
    spec = fixture_spec()
    spec["demo"]["demo"]["labels"].append({"text": "CLICK", "feature": "click"})
    spec["narration"]["hook"] = "This changes everything, and it has 12k stars."
    errs = " ".join(series.validate(spec, cfg()))
    assert "not tied to a verified feature" in errs
    assert "banned phrase" in errs
    assert "repository statistic" in errs


def test_feature_needs_evidence():
    spec = fixture_spec()
    spec["verified_features"][0]["evidence"] = ""
    spec["verified_features"][1]["status"] = "probably"
    errs = " ".join(series.validate(spec, cfg()))
    assert "no evidence" in errs and "status must be" in errs


def test_subtitle_groups_are_short_and_complete():
    text = "Would you actually use this? Follow Mimo for more GitHub discoveries. It tracks your hand through a webcam and turns gestures into computer controls."
    words = [{"w": w, "s": i * .4, "e": i * .4 + .3} for i, w in enumerate(text.split())]
    groups = series.subtitle_groups(words, ["GitHub", "webcam"])
    assert [w["w"] for g in groups for w in g["words"]] == text.split()
    assert max(len(g["words"]) for g in groups) <= 5
    assert all(g["e"] > g["s"] for g in groups)
    assert all(not any(w["w"].endswith((".", "?")) for w in g["words"][:-1]) for g in groups)      # never across a sentence end
    em = {w["w"] for g in groups for w in g["words"] if w["em"]}
    assert em == {"GitHub", "webcam"}


def test_caption_names_repo_and_episode_without_stats():
    text = series.caption(fixture_spec(), cfg(), 3)
    assert "EP. 003 of Mimo Found This on GitHub" in text
    assert "https://github.com/devmimo-fixtures/series-pipeline-test" in text
    assert "#GitHub" in text and "@devmimo" in text
    assert "stars" not in text.lower()


def test_rejected_candidate_never_holds_a_number():
    rejected = json.loads((ROOT / "series" / SLUG / "candidates" / "rejected.json").read_text())
    repos = {c["repository"].lower() for c in rejected["candidates"]}
    assert "fikriaf/handcam-control" in repos
    assert not any(r["repository"].lower() in repos for r in series.episodes(SLUG))


def test_compositions_registered_and_shared_components_episode_free():
    index = (ROOT / "src" / "index.tsx").read_text()
    for comp in ("SeriesEpisode", "SeriesCover", "SeriesCoverGuides"):
        assert f'id="{comp}"' in index
    for f in ("Cover.tsx", "Episode.tsx", "Visuals.tsx", "theme.ts"):
        src = (ROOT / "src" / "series" / f).read_text()
        assert "HandCam" not in src and "EP. 001" not in src and "fikriaf" not in src
    for name in ("SeriesHeader", "EpisodeNumber", "CoverHeadline", "BrandFooter", "CoverSafeZone"):
        assert f"export const {name}" in (ROOT / "src" / "series" / "Cover.tsx").read_text()
    assert "export const ProjectVisual" in (ROOT / "src" / "series" / "Visuals.tsx").read_text()
    assert "export const MimoMascot" in (ROOT / "src" / "series" / "Visuals.tsx").read_text()


def test_cue_frames_follow_label_order():
    import build_episode as be
    scene = {"frames": 200, "words": [{"w": "x", "s": i * .3, "e": i * .3 + .2} for i in range(20)]}
    labels = [{"text": "A", "feature": "a", "at": 3}, {"text": "B", "feature": "b", "at": 15}, {"text": "C", "feature": "c"}]
    frames = [be.label_frame(scene, labels, i) for i in range(3)]
    assert frames == sorted(frames)


def test_builder_makes_no_paid_calls():
    for f in ("build_episode.py", "qa_episode.py"):
        src = (ROOT / "examples" / "series" / f).read_text().lower()
        for banned in ("anthropic", "higgsfield", "requests.post", "urlopen"):
            assert banned not in src


def test_episode_001_spec_is_verified_and_numbered():
    spec = json.loads((ROOT / "series" / SLUG / "specs" / "harry0703-moneyprinterturbo.json").read_text())
    assert series.validate(spec, cfg()) == []
    rec = series.find_by_repo(SLUG, spec["repository"])
    assert rec and rec["episode"] == 1
    # every claim on screen is backed by evidence; anything not run is labelled source-only
    statuses = {f["id"]: f["status"] for f in spec["verified_features"]}
    assert statuses["script"] == "verified-source"
    assert all(statuses[l["feature"]] == "verified-run" for l in spec["demo"]["demo"]["labels"])
    import build_episode as be
    for ref in be.media_refs(spec):
        if ref.endswith(".png"):                       # mp4 renders are git-ignored; images are committed
            assert (ROOT / "public" / ref).exists(), ref
