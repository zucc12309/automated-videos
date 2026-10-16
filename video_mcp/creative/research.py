"""Research & verification: separate source facts from model framing, and map every narrated claim to its sources.

The creative director never invents research. It receives `research` (sources + facts, all untrusted text), and its
output is checked here: claims whose wording is not supported by any source are downgraded, and unsupported numeric
statements are removed from the narration.
"""
from __future__ import annotations

import re
import time

from ..schemas.storyboard import Claim, Source, Storyboard

STOP = set("a an the and or but of to in on for with from by is are was were be been it its this that these those you your "
           "we our they their as at into about can will just more most than then so not no yes do does did has have had "
           "how what why when who which one two three four five number new".split())


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9][a-z0-9.+#-]*", text.lower()) if w not in STOP and len(w) > 2}


def build_research(topic: dict) -> tuple[dict, list[Source]]:
    """Research packet for the director + Source records with retrieval timestamps."""
    retrieved = topic.get("retrieved_at") or topic.get("published") or time.time()
    sources: list[Source] = []
    facts: list[dict] = []
    if topic.get("kind") == "roundup":
        for i, repo in enumerate(topic.get("repos", []), 1):
            sid = f"src{i}"
            sources.append(Source(id=sid, url=repo.get("url", f"https://github.com/{repo['full_name']}")[:500], title=repo["full_name"][:250],
                                  kind="repository", retrieved_at=retrieved))
            facts.append({"source_id": sid, "verified_by": "GitHub REST API", "name": repo["name"], "owner": repo.get("owner"),
                          "description": repo.get("description", ""), "language": repo.get("language", ""),
                          "topics": repo.get("topics", []), "stars_on_screen_only": repo.get("stars"),
                          "readme_excerpt": (repo.get("readme_excerpt") or "")[:1500]})
        research = {"kind": "roundup", "theme": topic.get("theme", ""), "facts": facts}
    elif topic.get("kind") == "vibe_coding":
        sources.append(Source(id="src1", url=topic.get("url", "")[:500] or "https://code.claude.com/docs", title=topic["title"][:250], kind="manual",
                              retrieved_at=retrieved))
        research = {"kind": "vibe_coding", "title": topic["title"], "facts": [{"source_id": "src1", "text": topic.get("summary", ""),
                    "weak_prompt": topic.get("weak"), "better_prompt": topic.get("better"), "why": topic.get("why"),
                    "note": "editorial guidance from the curated tip library, not an executed result"}]}
    else:
        sid = "src1"
        if topic.get("url"):
            sources.append(Source(id=sid, url=topic["url"][:500], title=topic.get("title", "")[:250],
                                  kind="manual" if topic.get("kind") == "manual" else "article", retrieved_at=retrieved))
        research = {"kind": topic.get("kind", "story"), "title": topic.get("title", ""),
                    "facts": [{"source_id": sid if sources else "", "text": topic.get("summary", "")[:6000],
                               "note": "article text as fetched; may contain marketing language and announcements, not confirmed capabilities"}]}
    return research, sources


def source_texts(topic: dict, sources: list[Source]) -> dict[str, str]:
    if topic.get("kind") == "roundup":
        return {s.id: " ".join(str(v) for k, v in repo.items() if k not in ("stars", "url"))
                for s, repo in zip(sources, topic.get("repos", []))}
    return {s.id: f"{topic.get('title', '')} {topic.get('summary', '')}" for s in sources} or {"": topic.get("summary", "")}


def support(sentence: str, texts: dict[str, str], threshold: float = .5) -> tuple[list[str], float]:
    words = _tokens(sentence)
    if not words:
        return [], 1.0
    best, ids = 0.0, []
    for sid, text in texts.items():
        overlap = len(words & _tokens(text)) / len(words)
        if overlap >= threshold:
            ids.append(sid)
        best = max(best, overlap)
    return [i for i in ids if i], round(best, 3)


def verify(board: Storyboard, topic: dict) -> dict:
    """Attach claim->source mapping, downgrade unsupported 'verified' claims, and report what was changed."""
    texts = source_texts(topic, board.sources)
    all_text = " ".join(texts.values())
    report = {"checked_sentences": 0, "verified": 0, "interpretation": 0, "removed": [], "downgraded": []}
    claims = {c.id: c for c in board.claims}
    next_id = len(claims) + 1
    for scene in board.scenes:
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", scene.narration) if s.strip()]
        kept = []
        for sentence in sentences:
            report["checked_sentences"] += 1
            ids, overlap = support(sentence, texts)
            numbers = [n.rstrip(".,") for n in re.findall(r"\d[\d,.]*", sentence)]
            unsupported_numbers = [n for n in numbers if n.replace(",", "") not in all_text.replace(",", "")
                                   and not (n.isdigit() and int(n) <= 10)]
            if unsupported_numbers and scene.role not in ("hook", "outro"):
                report["removed"].append({"scene": scene.id, "sentence": sentence, "reason": f"numbers not in sources: {unsupported_numbers}"})
                continue
            kept.append(sentence)
            if scene.role in ("hook", "outro") or len(_tokens(sentence)) < 3:
                continue
            status = "verified" if ids else "interpretation"
            report[status] += 1
            matching = next((c for c in claims.values() if c.id in scene.claim_ids and _tokens(c.text) & _tokens(sentence)), None)
            if matching:
                if matching.status == "verified" and not ids:
                    matching.status = "unverified"
                    matching.note = f"automatic check found no source wording support (overlap {overlap})"
                    report["downgraded"].append(matching.id)
                matching.source_ids = sorted(set(matching.source_ids) | set(ids)) if ids else matching.source_ids
            else:
                cid = f"c{next_id}"
                next_id += 1
                claims[cid] = Claim(id=cid, text=sentence[:400], source_ids=ids, status=status,
                                    note=f"auto-mapped (word overlap {overlap})")
                scene.claim_ids.append(cid)
        if kept and len(kept) != len(sentences):
            scene.narration = " ".join(kept)
            if scene.emphasis and scene.emphasis.lower() not in scene.narration.lower():
                scene.emphasis = ""
            if scene.stat and scene.stat not in scene.narration:
                scene.stat = ""
    board.claims = list(claims.values())[:40]
    return report
