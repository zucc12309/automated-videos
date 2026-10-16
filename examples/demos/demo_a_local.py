"""Test A — LOCAL editorial reel: "Three useful developer tools".

Preferred path: repository facts fetched live from the GitHub REST API (a roundup; star counts shown on screen come from
the API). If the API is unreachable (offline, rate-limited, or a sandbox that blocks it), the demo falls back to a manual
topic made of README-level descriptions supplied by the operator — no numbers — and records that in provenance.

Script: Ollama if running, otherwise the deterministic template writer. Voice: Kokoro, otherwise espeak-ng. No paid service.
Usage: .venv/bin/python examples/demos/demo_a_local.py
"""
import json
import time

import httpx

from video_mcp import engine, sources

REPOS = ["BurntSushi/ripgrep", "junegunn/fzf", "jesseduffield/lazygit"]
MANUAL_NOTES = (
    "Ripgrep is a line-oriented search tool that recursively searches the current directory for a regex pattern. "
    "By default ripgrep respects gitignore rules and automatically skips hidden files, directories and binary files. "
    "Fzf is a general-purpose command-line fuzzy finder that works with any list: files, command history, processes or git commits. "
    "Lazygit is a simple terminal user interface for git commands, so staging, committing and rebasing happen in one screen. "
    "Together these three tools keep search, selection and version control inside the terminal."
)


def live_topic():
    with httpx.Client(timeout=20, headers=sources.UA, follow_redirects=True) as client:
        repos = [sources.repo_facts(client, client.get(f"https://api.github.com/repos/{n}").raise_for_status().json()) for n in REPOS]
    return {"id": "demo-a-live", "kind": "roundup", "title": "3 useful developer tools", "theme": "useful developer tools",
            "series": "TOOLS", "repos": repos, "url": "", "published": time.time(), "retrieved_at": time.time(), "score": 0}


def manual_topic(reason: str):
    return {"id": "demo-a-manual", "kind": "manual", "title": "Three terminal tools developers keep installing",
            "summary": MANUAL_NOTES, "url": "https://github.com/BurntSushi/ripgrep", "published": time.time(),
            "retrieved_at": time.time(), "score": 0, "series": "TOOLS",
            "provenance_note": f"Operator-supplied README-level descriptions; live GitHub API unavailable ({reason})."}


if __name__ == "__main__":
    try:
        topic = live_topic()
    except Exception as exc:
        topic = manual_topic(str(exc)[:120])
    print(json.dumps(engine.start_job(topic=topic, mode="local", seed="demo-a"), indent=2))
