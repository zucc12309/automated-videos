"""Imported motion-graphics clips (e.g. exported from Claude's design/motion tools, After Effects, or any editor).

A clip is validated (real, decodable video, size cap), copied into data/motion_library/ under a content hash, and can
then be placed in a storyboard scene with `assets: [{"kind": "graphic", "path": "library:<id>"}]`. The scene renders it
full-stage with the narration and captions on top. Clips are local files: nothing is fetched from the network here.
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from .. import security
from .asset_manager import file_hash, probe_video

MAX_MB = 300


class MotionLibrary:
    def __init__(self, data_dir: Path):
        self.root = data_dir / "motion_library"
        self.root.mkdir(parents=True, exist_ok=True)

    def import_clip(self, source: Path, *, title: str = "", origin: str = "claude-motion") -> dict:
        source = Path(source).expanduser().resolve()
        if not source.is_file():
            raise ValueError(f"No such file: {source}")
        if source.suffix.lower() not in (".mp4", ".mov", ".webm", ".m4v"):
            raise ValueError("Motion clips must be .mp4, .mov, .webm or .m4v")
        if source.stat().st_size > MAX_MB * 1024 * 1024:
            raise ValueError(f"Clip larger than {MAX_MB} MB")
        probe = probe_video(source)
        ident = file_hash(source)[:16]
        target = self.root / f"{ident}{source.suffix.lower()}"
        shutil.copyfile(source, target)
        meta = {"id": ident, "file": target.name, "title": title[:120] or source.stem[:120], "origin": security.safe_name(origin, 40),
                "probe": probe, "imported_at": time.time(), "original_name": source.name[:200]}
        (self.root / f"{ident}.json").write_text(json.dumps(meta, indent=1))
        return meta

    def get(self, ident: str) -> dict:
        ident = security.safe_name(ident, 32)
        meta_path = self.root / f"{ident}.json"
        if not meta_path.exists():
            raise KeyError(f"Unknown motion clip {ident}")
        meta = json.loads(meta_path.read_text())
        return {**meta, "path": str(self.root / meta["file"])}

    def list(self) -> list[dict]:
        return [json.loads(p.read_text()) for p in sorted(self.root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)]
