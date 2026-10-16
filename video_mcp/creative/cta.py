"""Contextual CTA engine and resource preparation.

Keyword by content type (brand/cta_templates.json): roundup → LINK, vibe_coding → PROMPT, tutorials/agents → GUIDE,
code → CODE, tool comparisons → TOOLS. Narration is truthful: unless an authorized, working DM delivery integration is
configured (brand_profile.cta_dm_delivery_enabled — nothing in this repository can set up such an integration), the
video never promises automatic DMs; it says "Comment LINK for the repo list." Resources are prepared for manual sending.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _templates() -> dict:
    return json.loads((ROOT / "brand" / "cta_templates.json").read_text())


def _series() -> dict:
    return json.loads((ROOT / "brand" / "series.json").read_text())


def content_type(fmt: str, topic: dict | None) -> str:
    if fmt in ("roundup", "vibe_coding"):
        return fmt
    text = json.dumps(topic or {}).lower()
    if re.search(r"\b(mcp|agent|agents|tool use)\b", text):
        return "agents"
    return "story"


def plan(fmt: str, topic: dict | None, item_count: int, dm_enabled: bool = False) -> dict:
    kind = content_type(fmt, topic)
    series = _series()["series"].get(kind, {})
    keyword = series.get("cta", "GUIDE")
    tpl = _templates()["keywords"][keyword]
    dm = dm_enabled and _templates()["fulfillment"].get("dm_delivery_enabled", False)
    narration = (tpl["narration_dm"] if dm else tpl["narration_truthful"]).format(count=item_count)
    return {"keyword": keyword, "secondary": tpl["secondary"].format(count=item_count), "narration": narration,
            "series_label": series.get("label", ""), "content_type": kind,
            "fulfillment": "dm_automation" if dm else "manual: resources prepared in resources/, send dm_message.txt by hand",
            "dm_promised": dm}


def apply(board, cta: dict) -> None:
    """Rewrite the outro so the spoken line, on-screen keyword and fulfilment agree."""
    outro = board.scenes[-1]
    if outro.role != "outro":
        return
    outro.narration = cta["narration"]
    outro.heading = f"Comment {cta['keyword']}"[:65]
    outro.emphasis = cta["keyword"]
    outro.layout = "outroCTA"
    outro.points = []
    outro.cta = {k: cta[k] for k in ("keyword", "secondary", "fulfillment")}
    outro.character_action = "pointing"
    outro.pace = "pause"        # the keyword gets a beat of silence to land
    board.cta = cta


def write_resources(job_dir: Path, board, topic: dict | None) -> dict:
    """resources/: manifest, guide, prompt/code where relevant, and a ready-to-send DM message. Only verified data."""
    out = job_dir / "resources"
    out.mkdir(parents=True, exist_ok=True)
    cta = board.cta or {}
    items, files = [], []
    for r in board.repos:
        items.append({"type": "repository", "name": r.get("full_name") or r.get("name"), "url": r.get("url") or f"https://github.com/{r.get('full_name', '')}",
                      "description": r.get("description", ""), "verified_by": "GitHub metadata in topic data (see provenance)"})
    for s in board.sources:
        if not any(i["url"] == s.url for i in items):
            items.append({"type": "source", "name": s.title or s.url, "url": s.url, "verified_by": f"source {s.id}"})
    lines = [f"# {board.title}", "", board.creative_direction.core_message or "", ""]
    steps = [sc for sc in board.scenes if sc.role not in ("hook", "outro")]
    if steps and not board.repos:
        lines += ["## Step by step", ""]
        lines += [f"{i}. **{sc.heading}** — {sc.narration}" for i, sc in enumerate(steps, 1)]
        lines += ["", "## Sources", ""]
    for i, it in enumerate(items, 1):
        lines.append(f"{i}. **{it['name']}** — {it['url']}" + (f"\n   {it['description']}" if it.get("description") else ""))
    code = next((sc.visual.code for sc in board.scenes if sc.visual.code and sc.visual.code_language not in ("prompt",)), [])
    if code:
        (out / "example_code").mkdir(exist_ok=True)
        (out / "example_code" / "example.txt").write_text("\n".join(code) + "\n\n# Illustrative snippet from the video; not executed by this pipeline.\n")
        files.append("example_code/example.txt")
    if board.format == "vibe_coding":
        before = next((s.visual.prompt_before for s in board.scenes if s.visual.prompt_before), [])
        after = next((s.visual.prompt_after for s in board.scenes if s.visual.prompt_after), [])
        if after:
            (out / "prompt.md").write_text("# Prompt template\n\nInstead of:\n\n> " + "\n> ".join(before) + "\n\nUse:\n\n```text\n" + "\n".join(after) +
                                           "\n```\n\nAdapt the bracketed parts to your project. Guidance only; results depend on your codebase and model.\n")
            files.append("prompt.md")
    lines += ["", "_Prepared from the video's verified source data. Review before sending._"]
    (out / "guide.md").write_text("\n".join(lines) + "\n")
    files.append("guide.md")
    dm = [f"Hey! Here's what you asked for from \"{board.title}\":", ""]
    if steps and not board.repos:
        dm += [f"{i}. {sc.heading}" for i, sc in enumerate(steps, 1)] + [""]
    dm += [f"• {it['name']}: {it['url']}" for it in items[:8]]
    if "prompt.md" in files:
        dm += ["", "Prompt template:", *(next((s.visual.prompt_after for s in board.scenes if s.visual.prompt_after), []))]
    (out / "dm_message.txt").write_text("\n".join(dm) + "\n")
    files.append("dm_message.txt")
    manifest = {"keyword": cta.get("keyword"), "secondary": cta.get("secondary"), "fulfillment": cta.get("fulfillment", "manual"),
                "dm_promised_in_video": cta.get("dm_promised", False), "items": items, "files": files + ["resource_manifest.json"],
                "note": "No automatic DM delivery is configured. Send dm_message.txt manually to people who comment the keyword."}
    (out / "resource_manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
    return manifest
