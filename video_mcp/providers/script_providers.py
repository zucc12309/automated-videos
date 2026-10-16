"""Local script providers: Ollama (existing behaviour) and a deterministic no-LLM template writer (zero-dependency fallback)."""
from __future__ import annotations

import re

import httpx

from .base import ProviderError, ScriptResult


class OllamaProvider:
    name = "ollama"

    def __init__(self, settings):
        self.settings = settings

    def available(self) -> tuple[bool, str]:
        from .. import engine
        try:
            response = httpx.get(f"{engine.OLLAMA}/api/tags", timeout=2)
            response.raise_for_status()
            models = [m["name"] for m in response.json().get("models", [])]
        except Exception:
            import shutil
            if shutil.which("ollama") or __import__("pathlib").Path("/opt/homebrew/bin/ollama").exists():
                return True, "ollama installed (will be started)"
            return False, "Ollama is not running or installed"
        if self.settings.model not in models:
            return False, f"Ollama model {self.settings.model} is not pulled (have: {', '.join(models[:6]) or 'none'})"
        return True, "ready"

    def write_plan(self, topic: dict, count: int) -> ScriptResult:
        from .. import engine
        try:
            plan = engine.generate_plan(topic)
        except httpx.HTTPError as exc:
            raise ProviderError(self.name, "unavailable", str(exc)[:300]) from exc
        except RuntimeError as exc:
            kind = "invalid_output" if "valid plan" in str(exc) else "unavailable"
            raise ProviderError(self.name, kind, str(exc)[:300]) from exc
        return ScriptResult(plan=plan, provider=self.name, model=self.settings.model)


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text or "").strip())
    return [p for p in parts if 30 <= len(p) <= 260 and not re.search(r"https?://|www\.|[{}<>|]", p)]


def _clip_words(text: str, n: int) -> str:
    words = text.split()
    out = " ".join(words[:n])
    return out if len(words) <= n else out.rstrip(",;:") + "."


def _heading(text: str, limit: int = 30) -> str:
    from ..quality.quality_report import shorten
    return shorten(re.sub(r"\s+", " ", text).strip().rstrip("."), limit)


def _key_words(text: str, k: int = 3) -> list[str]:
    words = [w.strip(".,!?;:'\"()") for w in text.split()]
    stop = {"the", "and", "that", "with", "this", "from", "your", "into", "their", "about", "which", "have", "will", "they"}
    ranked = sorted({w for w in words if len(w) > 4 and w.lower() not in stop}, key=lambda w: (-len(w), w))
    return ranked[:k]


class TemplateProvider:
    """Extractive, deterministic writer. Uses only sentences and metadata present in the topic data, so it cannot invent
    facts, but its copy is plainer than a model's. Used when no language model is available."""
    name = "template"

    def __init__(self, settings):
        self.settings = settings

    def available(self) -> tuple[bool, str]:
        return True, "always available (deterministic, lower quality copy)"

    def write_plan(self, topic: dict, count: int) -> ScriptResult:
        from .. import engine
        roundup = topic.get("kind") == "roundup"
        scenes = []
        if roundup:
            repos = topic["repos"]
            theme = re.sub(r"^\d+\s+", "", topic.get("theme", "tools")).strip()
            core = re.sub(r"\b(you should install|worth stealing|blowing up)\b", "", theme).strip()
            hook = f"{len(repos)} {core} worth installing today."
            scenes.append({"heading": _heading(f"{len(repos)} {core} worth installing", 40), "narration": hook, "caption": hook,
                           "emphasis": str(len(repos))})
            for i, repo in enumerate(repos, 1):
                desc = re.sub(r"\s+", " ", repo.get("description") or "").strip().rstrip(".")
                desc = re.sub(r"https?://\S+", "", desc)
                name = re.sub(r"[-_]+", " ", repo["name"])
                line = f"Number {i}: {name}. {_clip_words(desc, 24) if desc else 'An open source project worth a look.'}"
                if not line.endswith((".", "!", "?")):
                    line += "."
                points = [x for x in [repo.get("language", ""), *(repo.get("topics") or [])] if x][:3] or ["Open source"]
                scenes.append({"heading": _heading(desc or name), "narration": line, "caption": line, "label": repo["name"][:28],
                               "points": [p[:30] for p in points], "emphasis": name.split()[0]})
            outro = "Save this, and install one before your next session."
            scenes.append({"heading": "Save this. Install one.", "narration": outro, "caption": outro, "emphasis": "Save"})
        else:
            facts = _sentences(topic.get("summary", ""))
            title = re.sub(r"\s+", " ", topic.get("title", "This story")).strip()
            hook = _clip_words(title, 12).rstrip(".") + "."
            scenes.append({"heading": _heading(title, 40), "narration": hook, "caption": hook})
            picked = facts[:count] if len(facts) >= count else facts + [title] * (count - len(facts))
            for i, fact in enumerate(picked, 1):
                line = _clip_words(fact, 34)
                kw = _key_words(line)
                scenes.append({"heading": _heading(line), "narration": line, "caption": line, "label": (kw[0] if kw else f"Fact {i}")[:28],
                               "points": [k[:30] for k in kw[:3]] or [f"Fact {i}"], "emphasis": kw[0] if kw else ""})
            outro = "Save this, and send it to the builder who needs it today."
            scenes.append({"heading": "Save this. Send it on.", "narration": outro, "caption": outro, "emphasis": "Save"})
        plan = engine.Plan(title=_clip_words(topic.get("title", "Untitled"), 14)[:100], scenes=scenes,
                           series=topic.get("series", "REPOS" if roundup else "FACTS"))
        plan = engine.shape_plan(plan, topic, len(scenes) - 2, strict=False)
        plan.source_urls = [r["url"] for r in topic.get("repos", [])] if roundup else ([topic["url"]] if topic.get("url") else [])
        return ScriptResult(plan=plan, provider=self.name, model="template-v1", notes=["deterministic extractive copy; no language model"])
