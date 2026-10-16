"""Resource awareness for a single-machine studio (designed for a 24 GB Apple Silicon Mac, works on Linux).

Heavy stages never overlap (one job at a time via data/render.lock). Within a job: the local LLM is unloaded before
narration/rendering, and Chromium render concurrency is reduced when free memory is low.
"""
from __future__ import annotations

import os
import platform
import re
import subprocess

import httpx

CHROMIUM_TAB_GB = 1.2     # observed order of magnitude per Remotion render tab at 1080x1920; conservative


def available_memory_gb() -> float | None:
    try:
        if platform.system() == "Darwin":
            out = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=5).stdout
            page = int(re.search(r"page size of (\d+)", out).group(1))
            free = sum(int(re.search(rf"{k}:\s+(\d+)", out).group(1)) for k in ("Pages free", "Pages inactive", "Pages speculative"))
            return round(free * page / 1e9, 2)
        return round(os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 1e9, 2)
    except (ValueError, OSError, AttributeError, subprocess.SubprocessError):
        return None


def total_memory_gb() -> float | None:
    try:
        return round(os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 1e9, 2)
    except (ValueError, OSError, AttributeError):
        return None


def render_concurrency(configured: int, available_gb: float | None, reserve_gb: float = 3.0) -> int:
    """Never more tabs than memory allows after keeping a reserve for the OS, FFmpeg and the worker."""
    if available_gb is None:
        return configured
    fit = int(max(0.0, available_gb - reserve_gb) // CHROMIUM_TAB_GB)
    return max(1, min(configured, fit))


def release_ollama(base_url: str, model: str) -> bool:
    """Ask Ollama to unload the model now (keep_alive=0) so its memory is free before speech synthesis and rendering."""
    try:
        httpx.post(f"{base_url}/api/generate", json={"model": model, "keep_alive": 0}, timeout=5).raise_for_status()
        return True
    except httpx.HTTPError:
        return False


def snapshot() -> dict:
    return {"platform": platform.platform(), "machine": platform.machine(), "cpus": os.cpu_count(),
            "memory_total_gb": total_memory_gb(), "memory_available_gb": available_memory_gb()}
