"""Topic sources: GitHub repo roundups and full-text stories. All fetched text is untrusted data."""
from __future__ import annotations

import calendar
import hashlib
import html
import re
import time
from datetime import datetime, timedelta, timezone

import feedparser
import httpx

UA = {"User-Agent": "LocalVideoMCP/0.2", "Accept": "application/vnd.github+json"}
MAX_BYTES = 3_000_000


def _ident(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _get(client: httpx.Client, url: str, **kwargs) -> httpx.Response:
    response = client.get(url, **kwargs)
    response.raise_for_status()
    if len(response.content) > MAX_BYTES:
        raise ValueError(f"Response from {url} exceeds size limit")
    return response


def clean_markdown(text: str, limit: int = 2200) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)          # images / badges
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)        # keep link text only
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[#>*_`|]+", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()[:limit]


def article_text(client: httpx.Client, url: str, limit: int = 4500) -> str:
    page = _get(client, url, headers={"User-Agent": "Mozilla/5.0 LocalVideoMCP"}).text
    page = re.sub(r"<(script|style|nav|header|footer|aside)[^>]*>.*?</\1>", " ", page, flags=re.S | re.I)
    paragraphs = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", p))).strip()
                  for p in re.findall(r"<p[^>]*>(.*?)</p>", page, flags=re.S | re.I)]
    return " ".join(p for p in paragraphs if len(p) > 60)[:limit]


def repo_facts(client: httpx.Client, item: dict) -> dict:
    full_name = item["full_name"]
    readme = ""
    try:
        readme = clean_markdown(_get(client, f"https://api.github.com/repos/{full_name}/readme",
                                     headers={**UA, "Accept": "application/vnd.github.raw"}).text)
    except Exception:
        pass
    return {"full_name": full_name, "name": item["name"], "owner": item["owner"]["login"],
            "description": (item.get("description") or "")[:240], "stars": item["stargazers_count"],
            "language": item.get("language") or "", "topics": item.get("topics", [])[:4],
            "url": item["html_url"], "readme_excerpt": readme}


def repo_roundups(cfg: dict, used_repos: set[str], used_ids: set[str]) -> tuple[list[dict], list[dict]]:
    """One candidate per configured theme: the freshest high-star repos not featured before."""
    results, errors = [], []
    created_after = (datetime.now(timezone.utc) - timedelta(days=cfg.get("repo_max_age_days", 120))).date().isoformat()
    count = cfg.get("roundup_size", 4)
    with httpx.Client(timeout=25, follow_redirects=True, headers=UA) as client:
        for theme in cfg.get("repo_themes", []):
            try:
                query = f"{theme['query']} created:>{created_after} stars:>{theme.get('min_stars', 100)}"
                items = _get(client, "https://api.github.com/search/repositories",
                             params={"q": query, "sort": "stars", "order": "desc", "per_page": 30}).json()["items"]
                must = re.compile(theme.get("must", "."), re.I)
                fresh = [x for x in items if x["full_name"] not in used_repos and not x.get("fork") and x.get("description")
                         and must.search(" ".join([x["name"], x["description"], *x.get("topics", [])]))][:count]
                if len(fresh) < 3:
                    continue
                ident = _ident(theme["name"] + "|" + ",".join(x["full_name"] for x in fresh))
                if ident in used_ids:
                    continue
                repos = [repo_facts(client, x) for x in fresh]
                results.append({"id": ident, "kind": "roundup", "title": f"{len(repos)} {theme['name']}", "theme": theme["name"],
                                "series": theme.get("series", "REPOS"), "repos": repos, "url": "",
                                "published": time.time(), "score": 10})
            except Exception as exc:
                errors.append({"source": f"github:{theme.get('name')}", "error": str(exc)})
    return results, errors


def stories(cfg: dict, used_ids: set[str]) -> tuple[list[dict], list[dict]]:
    results, errors, seen = [], [], set(used_ids)
    cutoff = time.time() - cfg["max_age_days"] * 86400
    with httpx.Client(timeout=25, follow_redirects=True, headers={"User-Agent": "LocalVideoMCP/0.2"}) as client:
        for url in cfg["feeds"]:
            try:
                feed = feedparser.parse(_get(client, url).content)
                candidates = []
                for entry in feed.entries[:60]:
                    link = entry.get("link", "")
                    if not link.startswith(("http://", "https://")):
                        continue
                    ident = _ident(link)
                    date = entry.get("published_parsed") or entry.get("updated_parsed")
                    timestamp = calendar.timegm(date) if date else 0
                    title = re.sub(r"<[^>]+>", " ", html.unescape(entry.get("title", ""))).strip()[:250]
                    summary = clean_markdown(entry.get("summary", ""), 1500)
                    score = sum(1 for word in cfg["keywords"] if re.search(r"\b" + re.escape(word) + r"\b", title + " " + summary, re.I))
                    if timestamp >= cutoff and ident not in seen and score:
                        candidates.append((score, timestamp, ident, link, title, summary))
                        seen.add(ident)
                for score, timestamp, ident, link, title, summary in sorted(candidates, reverse=True)[:4]:
                    try:
                        body = article_text(client, link)
                    except Exception:
                        body = ""
                    text = body if len(body) > len(summary) else summary
                    if len(text) < 600:
                        continue  # a headline alone produces vague scripts
                    results.append({"id": ident, "kind": "story", "title": title, "url": link, "summary": text,
                                    "published": timestamp, "score": score, "feed": url})
            except Exception as exc:
                errors.append({"source": url, "error": str(exc)})
    results.sort(key=lambda x: (x["score"], x["published"]), reverse=True)
    return results, errors


def vibe_topics(used_ids: set[str]) -> list[dict]:
    """Unused tips from the curated vibe-coding library (editorial guidance; no network)."""
    import json
    from pathlib import Path
    lib = json.loads((Path(__file__).parent / "content" / "vibe_library.json").read_text())
    out = []
    for tip in lib["tips"]:
        if tip["id"] in used_ids:
            continue
        out.append({**tip, "kind": "vibe_coding", "summary": tip["notes"], "url": lib["sources"].get(tip.get("source", ""), ""),
                    "series": "BUILD SMARTER", "published": time.time(), "score": 6})
    return out
