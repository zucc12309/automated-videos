"""Content-addressed cache for generated media, with validated downloads.

Cache key = sha256 of (provider, application/model id + version, prompt, generation params, reference-asset hashes, seed,
relevant provider config). Identical requests reuse the stored file instead of paying again.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import time
import uuid
from pathlib import Path

import httpx

from .. import security


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cache_key(*, provider: str, model: str, prompt: str, params: dict, reference_hashes: list[str], seed, config: dict) -> str:
    material = json.dumps({"provider": provider, "model": model, "prompt": prompt, "params": params, "refs": sorted(reference_hashes),
                           "seed": seed, "config": config}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(material.encode()).hexdigest()


def probe_video(path: Path) -> dict:
    """ffprobe + a full decode pass. Raises ValueError for anything that is not a playable video."""
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                             capture_output=True, text=True, check=True, timeout=60)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f"Not a readable media file: {exc}") from exc
    info = json.loads(out.stdout)
    video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    duration = float(info.get("format", {}).get("duration") or 0)
    if not video or duration <= 0:
        raise ValueError("Media has no video stream or zero duration")
    decode = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"], capture_output=True, text=True, timeout=300)
    if decode.returncode != 0 or decode.stderr.strip():
        raise ValueError(f"Decode errors: {decode.stderr.strip()[:300]}")
    return {"width": video.get("width"), "height": video.get("height"), "duration": duration, "codec": video.get("codec_name")}


class AssetManager:
    def __init__(self, data_dir: Path):
        self.root = data_dir / "assets"
        self.root.mkdir(parents=True, exist_ok=True)

    def lookup(self, key: str) -> dict | None:
        meta = self.root / key[:2] / key / "meta.json"
        if meta.exists():
            data = json.loads(meta.read_text())
            if (meta.parent / data["file"]).exists():
                return {**data, "path": str(meta.parent / data["file"])}
        return None

    def store(self, key: str, source: Path, meta: dict) -> dict:
        folder = self.root / key[:2] / key
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / ("asset" + (source.suffix or ".mp4"))
        shutil.copyfile(source, target)
        record = {**security.redact(meta), "file": target.name, "sha256": file_hash(target), "stored_at": time.time(), "key": key}
        (folder / "meta.json").write_text(json.dumps(record, indent=1))
        return {**record, "path": str(target)}

    def list(self, limit: int = 50) -> list[dict]:
        metas = sorted(self.root.glob("*/*/meta.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
        return [json.loads(p.read_text()) for p in metas]

    @staticmethod
    def download(url: str, dest: Path, max_mb: int = 300, timeout: float = 120) -> Path:
        """Fetch a provider output URL with SSRF checks, a size cap and media validation."""
        security.check_url(url, allowed_schemes=("https",))
        dest.parent.mkdir(parents=True, exist_ok=True)
        temp = dest.with_suffix(f".{uuid.uuid4().hex}.part")
        limit = max_mb * 1024 * 1024
        size = 0
        with httpx.Client(timeout=timeout, follow_redirects=False) as client, client.stream("GET", url) as response:
            if response.is_redirect:
                raise ValueError("Redirects are not followed for media downloads")
            response.raise_for_status()
            kind = response.headers.get("content-type", "")
            if kind and not kind.startswith(("video/", "application/octet-stream", "binary/")):
                raise ValueError(f"Unexpected content type {kind}")
            with temp.open("wb") as f:
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > limit:
                        raise ValueError(f"Download exceeds {max_mb} MB")
                    f.write(chunk)
        try:
            probe_video(temp)
        except ValueError:
            temp.unlink(missing_ok=True)
            raise
        temp.replace(dest)
        return dest
