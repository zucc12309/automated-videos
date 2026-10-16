import json
import shutil
from pathlib import Path

import pytest

from video_mcp import engine, settings

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def cfg_dict():
    return json.loads((ROOT / "config.json").read_text())


@pytest.fixture
def make_cfg(cfg_dict):
    def build(**sections):
        raw = json.loads(json.dumps(cfg_dict))
        for key, value in sections.items():
            if isinstance(value, dict):
                raw.setdefault(key, {}).update(value)
            else:
                raw[key] = value
        return settings.from_dict(raw)
    return build


@pytest.fixture
def job_dir(tmp_path):
    folder = tmp_path / "jobs" / "abcdef123456"
    folder.mkdir(parents=True)
    (folder / "status.json").write_text(json.dumps({"id": "abcdef123456", "state": "running", "phase": "PLANNING"}))
    return folder


@pytest.fixture
def example_plan():
    return engine.Plan.model_validate_json((ROOT / "examples/first-reel.json").read_text())


def have(binary):
    return shutil.which(binary) is not None
