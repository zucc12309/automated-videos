"""QA scoring, report files, and repair planning.

Scores are 0-100 per category and each carries its basis. Deterministic checks are measurements; heuristics are
pixel/energy rules of thumb; model opinions are only present when an optional vision review ran; everything else is
listed under manual review. A subjective score is never presented as an objective measurement.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import audio_analysis, frame_analysis, video_validation

MANUAL = ["Factual accuracy against the cited sources", "Pronunciation of names and acronyms", "Overall taste / brand fit",
          "Music licensing (procedural bed is generated locally)"]


def _score(checks: list[dict]) -> int | None:
    if not checks:
        return None
    return round(100 * sum(1 for c in checks if c["passed"]) / len(checks))


def run(video: Path, props: dict, narration: list[dict], storyboard: dict | None, qa_dir: Path, *, dark: bool = False) -> dict:
    qa_dir.mkdir(parents=True, exist_ok=True)
    fps = props["fps"]
    technical = video_validation.technical(video, width=props["width"], height=props["height"], fps=fps,
                                           expected_seconds=props["durationInFrames"] / fps, dark_theme=dark)
    layout = frame_analysis.layout_checks(props)
    frames = frame_analysis.frame_checks(video, props, qa_dir)
    audio = audio_analysis.analyze(video, narration)
    visual = {"layout_checks": layout["checks"], "frame_samples": frames["samples"], "issues": layout["issues"] + frames["issues"],
              "layout_order": layout["layout_order"], "contact_sheet": frames["contact_sheet"]}
    sources = {"claims": [], "summary": "no storyboard"}
    if storyboard:
        claims = storyboard.get("claims", [])
        sources = {"claims": claims, "summary": {s: sum(1 for c in claims if c["status"] == s) for s in ("verified", "interpretation", "unverified", "removed")}}
    by_kind = lambda kinds: [c for c in layout["checks"] if c.get("kind") in kinds]
    scores = {
        "technical_correctness": {"score": _score(technical["checks"]), "basis": "deterministic"},
        "readability": {"score": _score(by_kind({"overflow", "tiny_text", "caption", "contrast"})), "basis": "deterministic (layout metadata + tokens)"},
        "visual_consistency": {"score": _score(by_kind({"consistency", "occlusion", "missing_asset"})), "basis": "deterministic"},
        "motion_quality": {"score": 100 - min(100, 25 * len(technical["freeze_segments"])) if technical["checks"] else None,
                           "basis": "heuristic (freeze detection only; motion taste needs manual review)"},
        "scene_variety": {"score": _score(by_kind({"repetition"}) + [{"passed": i["kind"] != "repetition"} for i in frames["issues"]]),
                          "basis": "deterministic + heuristic"},
        "audio_quality": {"score": _score(audio["checks"]), "basis": "deterministic loudness/peak; heuristic caption sync"},
        "narrative_coherence": {"score": None, "basis": "manual review required (no model opinion collected)"},
        "source_reliability": {"score": round(100 * sources["summary"].get("verified", 0) / max(1, len(sources["claims"])))
                               if isinstance(sources["summary"], dict) and sources["claims"] else None,
                               "basis": "deterministic word-overlap support check; share of claims with source support"},
    }
    mandatory_fail = [c for c in technical["checks"] + audio["checks"] + layout["checks"] if c.get("mandatory") and not c["passed"]]
    failing_scenes = sorted({i.get("scene") for i in visual["issues"] if i.get("scene")})
    summary = {"technical_pass": technical["passed"] and not mandatory_fail, "mandatory_failures": mandatory_fail, "scores": scores,
               "failing_scenes": failing_scenes, "issue_count": len(visual["issues"]), "manual_review": MANUAL,
               "estimated_caption_timing": audio["estimated_timings"], "contact_sheet": frames["contact_sheet"]}
    for name, value in (("technical.json", technical), ("visual.json", visual), ("audio.json", audio),
                        ("storyboard.json", {"sources": sources}), ("summary.json", summary)):
        (qa_dir / name).write_text(json.dumps(value, indent=1, default=str))
    (qa_dir / "summary.md").write_text(markdown(summary, technical, visual, audio, sources))
    return {"summary": summary, "technical": technical, "visual": visual, "audio": audio}


def markdown(summary, technical, visual, audio, sources) -> str:
    lines = ["# QA summary", "", f"**Technical pass:** {'yes' if summary['technical_pass'] else 'NO'}", ""]
    lines += ["| Category | Score | Basis |", "|---|---|---|"]
    for k, v in summary["scores"].items():
        lines.append(f"| {k.replace('_', ' ')} | {v['score'] if v['score'] is not None else 'n/a'} | {v['basis']} |")
    lines += ["", "## Technical checks (deterministic)", ""]
    lines += [f"- {'PASS' if c['passed'] else 'FAIL'} `{c['check']}` — {c['detail']}" for c in technical["checks"]]
    lines += ["", "## Visual issues", ""]
    lines += [f"- [{i.get('basis')}] `{i.get('check')}` {i.get('scene') or ''}: {i.get('detail')}" for i in visual["issues"]] or ["- none"]
    lines += ["", "## Audio", ""]
    lines += [f"- {'PASS' if c['passed'] else 'FAIL'} `{c['check']}` — {c['detail']} ({c['basis']})" for c in audio["checks"]]
    if audio["estimated_timings"]:
        lines.append("- Caption timings are **estimated** (no model timestamps for this voice).")
    lines += ["", "## Sources", "", f"Claim status counts: {sources['summary']}", "", "## Manual review required", ""]
    lines += [f"- {m}" for m in summary["manual_review"]]
    return "\n".join(lines) + "\n"


# ---------- repair planning ----------

REPAIRS = {
    "overflow": "switch the scene to a layout with more text capacity",
    "tiny_text": "switch the scene to a layout with larger type",
    "occlusion": "hide the presenter for the scene",
    "missing_asset": "replace footage with the approved Remotion fallback",
    "blank": "replace the scene's opening layout",
    "repetition": "re-seed layout planning",
    "caption": "use the compact pill caption style",
    "contrast": "switch to the high-contrast carbon theme",
    "decode": "re-render",
}


def plan_repairs(report: dict, props: dict) -> dict:
    """Targeted overrides for build_props; only scenes with issues change."""
    overrides: dict = {"avoid": {}, "hide_character": [], "drop_media": [], "notes": []}
    for issue in report["visual"]["issues"]:
        kind, sid = issue.get("kind"), issue.get("scene")
        if kind in ("overflow", "tiny_text", "blank") and sid:
            scene = next((s for s in props["scenes"] if s.get("id") == sid), None)
            if scene:
                bad = {b["layout"] for b in scene["beats"] if kind != "blank" or b is scene["beats"][0]}
                overrides["avoid"].setdefault(sid, sorted(bad - {"repoCard", "recap", "loop"}))
        elif kind == "occlusion" and sid:
            overrides["hide_character"].append(sid)
        elif kind == "missing_asset" and sid:
            overrides["drop_media"].append(sid)
        elif kind == "repetition":
            overrides["reseed"] = True
        elif kind == "caption":
            overrides["captions"] = "pill"
        elif kind == "contrast":
            overrides["theme"] = "carbon"
        overrides["notes"].append(f"{sid or 'video'}: {kind} -> {REPAIRS.get(kind, 're-render')}")
    return overrides
