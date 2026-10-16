"""Hook candidates for the first two seconds.

Three truthful candidates are generated from the topic data (never from invented facts), scored on six criteria and
the best one opens the video. Every score is recorded so the choice is inspectable (storyboard.hook_candidates).
"""
from __future__ import annotations

import re

NICHE = {"claude", "claude code", "codex", "agent", "agents", "mcp", "github", "repo", "repos", "prompt", "prompts", "cursor", "ai", "coding", "llm"}
CURIOUS = re.compile(r"\b(stop|missing|never|nobody|secret|instead|wrong|actually|why|this|you're|your)\b|\?$", re.I)
VISUAL = re.compile(r"\b(repos?|prompts?|tools?|commands?|agents?|diagram|terminal|code|ui|workflow|server)\b", re.I)
HYPE = re.compile(r"\b(\d+x|10x|100x|insane|crazy|best ever|game.?changer|revolutionary|mind.?blowing|secret weapon)\b", re.I)


def score(text: str, allowed_numbers: set[str]) -> dict:
    words = text.split()
    clarity = 1.0 if len(words) <= 9 else max(0.0, 1 - (len(words) - 9) * .15)
    clarity -= .1 * sum(1 for w in words if len(w) > 12)
    numbers = re.findall(r"\d[\d,.]*", text)
    specificity = min(1.0, .45 * bool(numbers) + .35 * bool(re.search(r"\b[A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+)?\b", text[1:])) + .2 * bool(VISUAL.search(text)))
    relevance = min(1.0, sum(1 for k in NICHE if re.search(rf"\b{re.escape(k)}\b", text, re.I)) * .4)
    curiosity = .9 if CURIOUS.search(text) else .4
    visual = .9 if VISUAL.search(text) else .4
    unsupported = [n for n in numbers if n.replace(",", "") not in allowed_numbers]
    credibility = 0.0 if HYPE.search(text) or unsupported else 1.0
    parts = {"clarity": round(max(0, clarity), 2), "specificity": round(specificity, 2), "relevance": round(relevance, 2),
             "curiosity": curiosity, "visual_potential": visual, "credibility": credibility}
    total = 1.4 * parts["clarity"] + 1.0 * parts["specificity"] + 1.0 * parts["relevance"] + .8 * parts["curiosity"] + .6 * parts["visual_potential"]
    total = total * (1 if credibility else 0)          # an unsupported claim disqualifies the hook
    return {"text": text, "score": round(total, 3), "parts": parts, "unsupported": unsupported}


def _subject(topic: dict) -> str:
    text = " ".join([topic.get("theme", ""), topic.get("title", "")])
    for name in ("Claude Code", "Codex", "MCP", "Cursor", "coding agents", "AI agents"):
        if name.lower() in text.lower():
            return name
    return "your AI workflow"


def candidates(topic: dict, fmt: str, count: int) -> list[str]:
    subject = _subject(topic)
    if fmt == "roundup":
        return [f"{count} GitHub repos that make {subject} better.", f"Your {subject} setup is missing these {count} repos.",
                f"{count} {subject} repos worth installing today."]
    if fmt == "vibe_coding":
        problem = (topic.get("problem") or "breaks your code").rstrip(".")
        return [topic.get("hook") or "Stop giving your coding agent prompts like this.", f"Your coding agent {problem}?",
                f"One prompt change fixes this in {subject}."]
    title = re.sub(r"\s+", " ", topic.get("title", "")).strip().rstrip(".")
    return [f"{title}." if title else f"What changed in {subject} this week.", f"This changes how you use {subject}.",
            f"{count} things to know about {title or subject}."]


def choose(topic: dict, fmt: str, count: int, source_text: str) -> tuple[str, list[dict]]:
    allowed = {re.sub(r",", "", n).rstrip(".") for n in re.findall(r"\d[\d,.]*", source_text)} | {str(count)} | {str(i) for i in range(11)}
    scored = sorted((score(c, allowed) for c in candidates(topic, fmt, count)), key=lambda x: (-x["score"], len(x["text"])))
    return scored[0]["text"], scored
