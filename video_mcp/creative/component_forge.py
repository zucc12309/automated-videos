"""Controlled path for new Remotion components (written by Claude or a person) to become reusable layouts.

1. spec        name, intents it serves, data it needs
2. static scan allow-listed imports only; no eval/Function/require/dynamic import, network, storage, timers, randomness,
               process/global access, raw HTML injection, or external URLs
3. isolate     written to src/studio/generated/pending/ (never imported by the production composition)
4. typecheck   `tsc --noEmit` on the pending file
5. smoke test  `remotion still` of a sandbox composition, with an environment stripped of credentials
6. screenshot  the still must not be blank
7. register    status "pending_review" in registry.json
8. promote     only an explicit `promote` call moves it to approved/ and adds it to GENERATED (and the router catalog)

Unattended production uses approved components only; nothing generated is ever evaluated with eval().
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np

from .. import security

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "src" / "studio" / "generated"
ALLOWED_IMPORTS = {"react", "remotion", "../../kit", "../../motion", "../../tokens", "../../../shared"}
BANNED = [r"\beval\s*\(", r"\bnew\s+Function\b", r"\bFunction\s*\(", r"\brequire\s*\(", r"\bimport\s*\(", r"\bprocess\b", r"\bglobalThis\b",
          r"\bwindow\b", r"\bdocument\b", r"\bfetch\s*\(", r"XMLHttpRequest", r"WebSocket", r"localStorage", r"sessionStorage", r"indexedDB",
          r"child_process", r"\bfs\b", r"Math\.random", r"Date\.now", r"new\s+Date", r"setTimeout", r"setInterval", r"requestAnimationFrame",
          r"dangerouslySetInnerHTML", r"<script", r"<iframe", r"https?://", r"\bdelayRender\b", r"\bnavigator\b", r"postMessage", r"__proto__"]


def scan(name: str, source: str) -> list[str]:
    problems = []
    if not re.fullmatch(r"[A-Z][A-Za-z0-9]{2,40}", name):
        problems.append("name must be PascalCase, 3-41 chars")
    for spec in re.findall(r"""import\s+[^'"]*?from\s+['"]([^'"]+)['"]""", source) + re.findall(r"""import\s+['"]([^'"]+)['"]""", source):
        if spec not in ALLOWED_IMPORTS:
            problems.append(f"import not allowed: {spec}")
    for pattern in BANNED:
        if re.search(pattern, source):
            problems.append(f"forbidden construct: {pattern}")
    if not re.search(rf"export\s+const\s+{name}\s*:\s*React\.FC<LayoutProps>", source):
        problems.append(f"must export `const {name}: React.FC<LayoutProps>`")
    if len(source) > 20000:
        problems.append("component too large (> 20 kB)")
    return problems


def _registry() -> dict:
    path = GEN / "registry.json"
    return json.loads(path.read_text()) if path.exists() else {"components": {}}


def _save_registry(data: dict):
    (GEN / "registry.json").write_text(json.dumps(data, indent=1) + "\n")


SANDBOX = """import React from 'react';
import {{AbsoluteFill, Composition, registerRoot}} from 'remotion';
import {{{name}}} from './{name}';
import {{STAGE, THEMES, DEFAULT_VARIANT}} from '../../tokens';

const P = THEMES['carbon'];
const scene: any = {{heading: 'Sandbox heading', narration: 'A sample line for the sandbox render with 72% in it.', caption: '', stat: '72%', points: ['First point', 'Second point', 'Third point'],
  visual: 'cards', audio: '', frames: 90, from: 0, words: [], beats: [], visualData: {{code: ['npm install example'], nodes: ['Client', 'Server', 'Model'],
  steps: ['Plan', 'Build', 'Ship'], timeline: ['2024: start', '2025: grow', '2026: ship'], series_labels: ['A', 'B', 'C'], series_values: [1, 2, 3],
  compare_left: ['Old'], compare_right: ['New'], compare_titles: ['Before', 'After']}}}};
const beat: any = {{s: 0, e: 3, w: [0, 0], text: 'sample line', focus: 'sandbox', layout: '{name}', anchor: 'right', transition: 'cut', punch: false}};
const props: any = {{title: 'Sandbox', scenes: [scene], durationInFrames: 90, fps: 30, width: 1080, height: 1920}};
const Sandbox = () => <AbsoluteFill style={{{{background: P.bg}}}}>
  <div style={{{{position: 'absolute', left: STAGE.left, top: STAGE.top, width: STAGE.width, height: STAGE.height}}}}>
    <{name} beat={{beat}} scene={{scene}} props={{props}} P={{P}} v={{DEFAULT_VARIANT}} index={{0}} hit={{null}} dur={{90}}/>
  </div>
</AbsoluteFill>;
registerRoot(() => <Composition id="Sandbox" component={{Sandbox}} durationInFrames={{90}} fps={{30}} width={{1080}} height={{1920}}/>);
"""


def submit(name: str, source: str, *, intents: list[str], needs: list[str] | None = None, browser: str = "", timeout: int = 300) -> dict:
    record = {"name": name, "intents": intents, "needs": needs or [], "submitted_at": time.time(), "status": "rejected", "steps": []}
    problems = scan(name, source)
    record["steps"].append({"step": "static_scan", "passed": not problems, "problems": problems})
    if problems:
        return _store(record)
    pending = GEN / "pending"
    pending.mkdir(parents=True, exist_ok=True)
    (pending / f"{name}.tsx").write_text(source)
    entry = pending / f"{name}.entry.tsx"
    entry.write_text(SANDBOX.format(name=name))
    env = security.child_env()
    tsc = subprocess.run([str(ROOT / "node_modules/.bin/tsc"), "--noEmit", "--jsx", "react-jsx", "--strict", "--skipLibCheck", "--esModuleInterop",
                          "--resolveJsonModule", "--moduleResolution", "bundler", "--module", "esnext", "--target", "es2020", str(entry)],
                         cwd=ROOT, capture_output=True, text=True, timeout=timeout, env=env)
    record["steps"].append({"step": "typecheck", "passed": tsc.returncode == 0, "output": (tsc.stdout + tsc.stderr)[-1500:]})
    if tsc.returncode:
        return _store(record)
    still = pending / f"{name}.png"
    args = [str(ROOT / "node_modules/.bin/remotion"), "still", str(entry.relative_to(ROOT)), "Sandbox", str(still), "--frame=60", "--log=error"]
    if browser:
        args.append(f"--browser-executable={browser}")
    render = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout, env=env)
    record["steps"].append({"step": "render_smoke_test", "passed": render.returncode == 0 and still.exists(), "output": render.stderr[-1500:]})
    if render.returncode or not still.exists():
        return _store(record)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(still), "-vf", "scale=270:480", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True, timeout=60).stdout
    stage = np.frombuffer(raw, dtype=np.uint8).reshape(480, 270)[90:265, 30:240] if len(raw) == 270 * 480 else np.zeros((1, 1))
    visible = float(stage.std()) > 4
    record["steps"].append({"step": "screenshot_validation", "passed": visible, "stage_std": round(float(stage.std()), 2)})
    record["status"] = "pending_review" if visible else "rejected"
    record["screenshot"] = str(still.relative_to(ROOT))
    return _store(record)


def _store(record: dict) -> dict:
    data = _registry()
    data["components"][record["name"]] = record
    _save_registry(data)
    return record


def promote(name: str, reviewer: str) -> dict:
    """Human (or explicitly authorised) review step: move a passing component into the production library."""
    data = _registry()
    record = data["components"].get(name)
    if not record or record.get("status") != "pending_review":
        raise ValueError(f"{name} is not awaiting review")
    source = (GEN / "pending" / f"{name}.tsx").read_text()
    if scan(name, source):
        raise ValueError("source changed since review and no longer passes the static scan")
    approved = GEN / "approved"
    approved.mkdir(exist_ok=True)
    (approved / f"{name}.tsx").write_text(source)
    record.update(status="approved", promoted_at=time.time(), reviewer=reviewer)
    _save_registry(data)
    _write_index(data)
    for suffix in (".tsx", ".entry.tsx", ".png"):
        (GEN / "pending" / f"{name}{suffix}").unlink(missing_ok=True)
    return record


def _write_index(data: dict):
    names = sorted(n for n, r in data["components"].items() if r.get("status") == "approved")
    lines = ["// Generated by video_mcp/creative/component_forge.py when a reviewed component is promoted. Do not edit by hand.",
             "import React from 'react';", "import {LayoutProps} from '../kit';"]
    lines += [f"import {{{n}}} from './approved/{n}';" for n in names]
    key = lambda n: n[0].lower() + n[1:]
    lines += ["", "export const GENERATED: Record<string, React.FC<LayoutProps>> = {" + ", ".join(f"{key(n)}: {n}" for n in names) + "};", ""]
    (GEN / "index.ts").write_text("\n".join(lines))


def approved_specs() -> list[dict]:
    """Approved components for the semantic router catalogue."""
    return [{"layout": n[0].lower() + n[1:], **r} for n, r in _registry()["components"].items() if r.get("status") == "approved"]
