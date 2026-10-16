"""Recurring series: episode registry, numbering, spec validation, subtitles and captions.

A series lives in `series/<slug>/`:

    series.json            name, tagline, palette, pacing, banned phrases (shared by every episode)
    specs/*.json           one authored spec per episode (repository, title, headline, verified features, demo)
    episodes/episode-NNN.json  the registry: one record per allocated number, never overwritten
    candidates/rejected.json   repositories checked and not produced (they never take a number)

Numbering rules:
- the next number is one above the highest number in the registry (reserved, draft, rendered or published);
- a repository that already has a record keeps its number, so re-rendering never allocates a new one;
- a manual override is honoured only if that number is free (or already belongs to the same repository);
- records are created with O_EXCL, so two builds can never write the same number.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERIES_ROOT = ROOT / "series"
STATUSES = ("reserved", "draft", "rendered", "published")
DEMO_STATUSES = {
    "captured": "a real screen/webcam capture of the project running",
    "run-in-sandbox": "the project's own code was run in the build environment; the picture re-draws that run",
    "source-reenactment": "a deterministic re-enactment of behaviour confirmed in the source; the project was not run",
    "project-showcase": "official output examples published by the project itself (shown muted and credited); the features they show were also verified in source or by a local run",
    "fixture": "pipeline test content, not an episode",
}
FEATURE_STATUSES = {"verified-run", "verified-source"}


class SeriesError(ValueError):
    pass


def series_dir(slug: str, root: Path | None = None) -> Path:
    return (root or SERIES_ROOT) / slug


def config(slug: str, root: Path | None = None) -> dict:
    return json.loads((series_dir(slug, root) / "series.json").read_text())


def fmt(n: int) -> str:
    """EP. 001 … EP. 010 … EP. 100 (three digits, wider numbers are kept whole)."""
    if n < 1:
        raise SeriesError(f"episode numbers start at 1, got {n}")
    return f"EP. {n:03d}"


def slugify_repo(repo: str) -> str:
    repo = normalize_repo(repo)
    return re.sub(r"[^a-z0-9]+", "-", repo.lower()).strip("-")


def normalize_repo(repo: str) -> str:
    """'https://github.com/Owner/Name(.git)' or 'Owner/Name' -> 'Owner/Name'."""
    m = re.match(r"^(?:https?://)?(?:www\.)?(?:github\.com/)?([A-Za-z0-9-]+)/([A-Za-z0-9._-]+?)(?:\.git)?/?$", repo.strip())
    if not m:
        raise SeriesError(f"not a GitHub repository: {repo!r}")
    return f"{m.group(1)}/{m.group(2)}"


# ---------------------------------------------------------------- registry
def episodes(slug: str, root: Path | None = None) -> list[dict]:
    d = series_dir(slug, root) / "episodes"
    out = []
    for p in sorted(d.glob("episode-*.json")):
        rec = json.loads(p.read_text())
        if rec.get("episode") != int(p.stem.split("-")[1]):
            raise SeriesError(f"{p.name} holds episode {rec.get('episode')}; the file name and record disagree")
        out.append(rec)
    return out


def find_by_repo(slug: str, repo: str, root: Path | None = None) -> dict | None:
    key = normalize_repo(repo).lower()
    for rec in episodes(slug, root):
        if rec["repository"].lower() == key:
            return rec
    return None


def record_path(slug: str, n: int, root: Path | None = None) -> Path:
    return series_dir(slug, root) / "episodes" / f"episode-{n:03d}.json"


def allocate(slug: str, repo: str, title: str, override: int | None = None, root: Path | None = None) -> tuple[dict, bool]:
    """Return (record, created). An existing repository keeps its number; otherwise the next free number is reserved."""
    repo = normalize_repo(repo)
    existing = find_by_repo(slug, repo, root)
    if existing:
        if override is not None and override != existing["episode"]:
            raise SeriesError(f"{repo} is already {fmt(existing['episode'])}; refusing to renumber it to {fmt(override)}")
        return existing, False
    (series_dir(slug, root) / "episodes").mkdir(parents=True, exist_ok=True)
    n = override if override is not None else max((r["episode"] for r in episodes(slug, root)), default=0) + 1
    while True:
        fmt(n)
        rec = {"series": slug, "episode": n, "label": fmt(n), "repository": repo, "title": title, "status": "reserved",
               "reserved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        try:
            fd = os.open(record_path(slug, n, root), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            if override is not None:
                taken = json.loads(record_path(slug, n, root).read_text())
                raise SeriesError(f"{fmt(n)} already belongs to {taken['repository']}; it will not be overwritten") from None
            n += 1                       # another build took this number between the scan and the create
            continue
        with os.fdopen(fd, "w") as f:
            json.dump(rec, f, indent=2)
        return rec, True


def update(slug: str, n: int, root: Path | None = None, **fields) -> dict:
    """Merge fields into an existing record. Number and repository are immutable; status only moves forward."""
    path = record_path(slug, n, root)
    rec = json.loads(path.read_text())
    for k in ("episode", "repository", "series"):
        if k in fields and fields[k] != rec[k]:
            raise SeriesError(f"{k} of {fmt(n)} cannot change")
    if "status" in fields and STATUSES.index(fields["status"]) < STATUSES.index(rec["status"]):
        fields = {k: v for k, v in fields.items() if k != "status"}         # re-rendering a published episode keeps it published
    rec.update(fields)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(rec, indent=2))
    tmp.replace(path)
    return rec


# ---------------------------------------------------------------- spec
def default_narration(spec: dict, cfg: dict) -> dict:
    t = cfg["narration_templates"]
    n = dict(spec.get("narration", {}))
    n.setdefault("hook", spec["title"].rstrip(".") + ".")
    n.setdefault("discovery", t["discovery"])
    n.setdefault("payoff", t["payoff"])
    return n


def validate(spec: dict, cfg: dict) -> list[str]:
    """Problems that block a render. Claims must trace to verified features; nothing hype or unverifiable reaches the screen."""
    errs = []
    for k in ("repository", "title", "cover_headline", "verified_features", "demo", "narration"):
        if not spec.get(k):
            errs.append(f"missing {k}")
    if errs:
        return errs
    try:
        normalize_repo(spec["repository"])
    except SeriesError as e:
        errs.append(str(e))
    feats = {f["id"]: f for f in spec["verified_features"]}
    for f in spec["verified_features"]:
        if f.get("status") not in FEATURE_STATUSES:
            errs.append(f"feature {f['id']}: status must be one of {sorted(FEATURE_STATUSES)}")
        if not f.get("evidence"):
            errs.append(f"feature {f['id']}: no evidence (file:line, test or capture)")
    demo = spec["demo"]
    if demo.get("status") not in DEMO_STATUSES:
        errs.append(f"demo.status must be one of {sorted(DEMO_STATUSES)}")
    for scene in ("hook", "demo"):
        for label in demo.get(scene, {}).get("labels", []):
            if label.get("feature") not in feats:
                errs.append(f"demo.{scene} label {label.get('text')!r} is not tied to a verified feature")
    for i, node in enumerate(spec.get("flow", [])):
        if node.get("feature") and node["feature"] not in feats:
            errs.append(f"flow node {i} cites unknown feature {node['feature']!r}")
    narration = default_narration(spec, cfg)
    for k in ("hook", "discovery", "demo", "tech", "payoff"):
        if not narration.get(k):
            errs.append(f"narration.{k} is empty")
    text = " ".join([spec["title"], " ".join(spec["cover_headline"]), *narration.values(), spec.get("caption", {}).get("hook", ""),
                     spec.get("caption", {}).get("body", "")]).lower()
    for phrase in cfg["banned_phrases"]:
        if re.search(r"\b" + re.escape(phrase) + r"\b", text):
            errs.append(f"banned phrase: {phrase!r}")
    for stat in cfg["unverifiable_stats"]:
        if re.search(r"\d[\d.,]*\s*k?\+?\s*" + stat + r"\b", text):
            errs.append(f"repository statistic in copy ({stat}); the series never quotes stars, downloads or similar")
    if spec.get("hardware_claim") and not any(f["id"] == spec["hardware_claim"] for f in spec["verified_features"]):
        errs.append("the 'no special hardware' line needs a verified feature backing it")
    return errs


# ---------------------------------------------------------------- subtitles
def _norm(w: str) -> str:
    return re.sub(r"[^a-z0-9+#]", "", w.lower())


def subtitle_groups(words: list[dict], emphasis: list[str] | None = None, min_words: int = 3, max_words: int = 5,
                    gap_s: float = .32) -> list[dict]:
    """Short phrases (3–5 words) that break at punctuation and at pauses, never across a sentence end.

    words: [{"w", "s", "e"}] on one clock. Returns [{"s", "e", "words": [{"w", "em"}]}] where e reaches the next group's start
    (or the last word's end + 0.3 s), so a phrase never blinks off between words."""
    emph = {_norm(x) for term in (emphasis or []) for x in term.split()}
    # 1. segments end at sentence ends, clause punctuation and audible pauses
    segments, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        if nxt is None or re.search(r"[.!?,;:]$", w["w"]) or nxt["s"] - w["e"] > gap_s:
            segments.append(cur)
            cur = []
    # 2. a one-word clause joins its neighbour in the same sentence when the result still fits
    joined = []
    for seg in segments:
        prev = joined[-1] if joined else None
        if prev and (len(seg) == 1 or len(prev) == 1) and len(prev) + len(seg) <= max_words and not re.search(r"[.!?]$", prev[-1]["w"]):
            joined[-1] = prev + seg
        else:
            joined.append(seg)
    # 3. long segments split into even phrases (7 words -> 4 + 3, never 5 + 2)
    merged = []
    for seg in joined:
        k = -(-len(seg) // max_words)
        size, extra = divmod(len(seg), k)
        at = 0
        for j in range(k):
            n = size + (1 if j < extra else 0)
            merged.append(seg[at:at + n])
            at += n
    out = []
    for i, g in enumerate(merged):
        end = merged[i + 1][0]["s"] if i + 1 < len(merged) else g[-1]["e"] + .3
        end = min(end, g[-1]["e"] + .6)
        out.append({"s": round(g[0]["s"], 3), "e": round(end, 3),
                    "words": [{"w": x["w"], "em": _norm(x["w"]) in emph} for x in g]})
    return out


# ---------------------------------------------------------------- copy
def caption(spec: dict, cfg: dict, n: int) -> str:
    c = spec.get("caption", {})
    repo = normalize_repo(spec["repository"])
    tags = list(dict.fromkeys(cfg["hashtags_base"][:2] + spec.get("hashtags", []) + cfg["hashtags_base"][2:]))
    parts = [c.get("hook", f"I found a GitHub project: {spec['title'].rstrip('.')}.") + " 👀",
             c["body"] if c.get("body") else None,
             f"Welcome to {fmt(n)} of {cfg['name']}. 👾",
             c.get("question", "Would you actually use this?"),
             f"Repo: {repo}\nhttps://github.com/{repo}",
             f"Follow {cfg['handle']} for more weird finds and real builds.",
             " ".join(tags)]
    return "\n\n".join(p for p in parts if p) + "\n"


def script_markdown(spec: dict, cfg: dict, n: int, scenes: list[dict], wpm: float, words: int) -> str:
    lines = [f"# {fmt(n)} · {spec['title']}", "", f"{cfg['name']} · repository: https://github.com/{normalize_repo(spec['repository'])}",
             f"Demo status: **{spec['demo']['status']}** ({DEMO_STATUSES[spec['demo']['status']]})", "",
             "| Scene | Start | Length | Narration |", "|---|---|---|---|"]
    for s in scenes:
        lines.append(f"| {s['id']} | {s['from'] / 30:.2f}s | {s['frames'] / 30:.2f}s | {s.get('narration', '—')} |")
    lines += ["", f"{words} words, {wpm:.0f} wpm while speaking.", "", "## Verified features shown", ""]
    for f in spec["verified_features"]:
        lines.append(f"- **{f['label']}** ({f['status']}): {f['claim']} — evidence: {f['evidence']}")
    return "\n".join(lines) + "\n"
