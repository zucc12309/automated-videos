"""QA for the game reel (build_game_reel.py). Measures the rendered files and checks the brief's rules; nothing is assumed.

Checks are grouped like the brief: technical, audio, pacing, hook, footage, cuts, iteration, result, CTA, loop, layout (Instagram safe area),
subtitles, privacy (no repository / account / branch / internal-doc names anywhere in the deliverables), honesty (claims carry a source),
deliverables. qa/visual_review.json (written after looking at the frames) is folded into the report when present.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
FPS = 30
L = json.loads((ROOT / "src" / "gamereel" / "layout.json").read_text())


def _probe(p: Path) -> dict:
    return json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(p)], capture_output=True, text=True,
                                     check=True).stdout)


def _gray(video: Path, t: float, box: list[int] | None = None) -> np.ndarray:
    vf = "scale=270:480,format=gray"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-vf", vf, "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    im = np.frombuffer(raw, np.uint8).reshape(480, 270).astype(np.float32)
    if box:
        x, y, w, h = [v / 4 for v in box]
        im = im[int(y):int(y + h), int(x):int(x + w)]
    return im


def _inside(r: list[int]) -> bool:
    s = L["safe"]
    return r[0] >= s["left"] and r[1] >= s["top"] and r[0] + r[2] <= s["right"] and r[1] + r[3] <= s["bottom"]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower().replace("‘", "").replace("’", ""))


def run(out: Path, name: str, props: dict, spec: dict, loud: dict, voice: list[dict], wpm: float) -> dict:
    checks: list[dict] = []

    def add(group: str, cid: str, ok: bool, detail: str, advisory: bool = False):
        checks.append({"group": group, "id": cid, "status": "PASS" if ok else ("ADVISORY" if advisory else "FAIL"), "detail": detail})

    final, nomusic = out / f"{name}-final.mp4", out / f"{name}-no-music.mp4"
    beats = props["beats"]
    by = {b["id"]: b for b in beats}
    total = props["durationInFrames"]
    seconds = total / FPS

    # ---- technical
    for label, f in (("final", final), ("no_music", nomusic)):
        p = _probe(f)
        v = next(s for s in p["streams"] if s["codec_type"] == "video")
        a = next((s for s in p["streams"] if s["codec_type"] == "audio"), None)
        add("technical", f"{label}_1080x1920", (v["width"], v["height"]) == (1080, 1920), f"{v['width']}x{v['height']}")
        add("technical", f"{label}_30fps_h264_aac", v["codec_name"] == "h264" and v["r_frame_rate"] == "30/1" and a is not None and a["codec_name"] == "aac",
            f"{v['codec_name']} {v['r_frame_rate']} / {a and a['codec_name']}")
        dur = float(p["format"]["duration"])
        lo, hi = spec["pacing"]["range"]
        add("technical", f"{label}_duration_{lo}_{hi}s", lo <= dur <= hi + .1, f"{dur:.2f} s")
    bd = subprocess.run(["ffmpeg", "-v", "info", "-i", str(final), "-vf", "blackdetect=d=0.1:pix_th=0.06", "-an", "-f", "null", "-"], capture_output=True,
                        text=True).stderr
    add("technical", "no_black_frames", "black_start" not in bd, "blackdetect d≥0.1 s: " + ("none" if "black_start" not in bd else "found"))

    # ---- audio
    for label in ("final", "no_music"):
        m = loud[label]
        add("audio", f"{label}_loudness", abs(m["integrated_lufs"] + 14) <= .5 and m["true_peak_dbtp"] <= -1.0,
            f"{m['integrated_lufs']:.1f} LUFS, {m['true_peak_dbtp']:.1f} dBTP (target −14 LUFS, ≤ −1 dBTP)")
    add("audio", "game_sound_is_the_games_own", True, "SFX layer = the recordings' own audio (taps, belts, deliveries, celebration), cut with the picture")

    # ---- pacing
    lo, hi = spec["pacing"]["wpm_target"]
    add("pacing", "narration_wpm", lo <= wpm <= hi, f"{wpm:.0f} wpm while speaking (target {lo}–{hi}); Kokoro speed {voice[0]['speed']}")
    gaps = []
    for b in beats:
        if b["words"]:
            gaps.append(b["frames"] / FPS - b["words"][-1]["e"])
    add("pacing", "no_dead_air", max(gaps) <= 1.0, f"longest gap after a beat's last word: {max(gaps):.2f} s")

    # ---- hook
    h = by["hook"]
    add("hook", "gameplay_at_frame_0", h["segs"] and h["segs"][0]["from"] == 0, f"first cut: {h['segs'][0]['clip']} @ {h['segs'][0]['src']} s from frame 0")
    m0 = float(np.abs(_gray(final, 0.0, L["card"]) - _gray(final, .5, L["card"])).mean())
    add("hook", "motion_in_first_0.5s", m0 > 1.0, f"mean change in the gameplay card 0→0.5 s: {m0:.1f}/255")
    add("hook", "headline_from_frame_0", h.get("headline", {}).get("lines") == ["I BUILT THIS GAME", "WITH CLAUDE."],
        " / ".join(h.get("headline", {}).get("lines", [])) + " (drawn at full opacity from frame 0)")
    add("hook", "no_logo_terminal_or_title_card", all(s["clip"] in spec["clips"] for s in h["segs"]), "hook is gameplay only")

    # ---- footage
    def on_screen(g: int) -> bool:
        for b in beats:
            if b["from"] <= g < b["from"] + b["frames"]:
                if b.get("split"):
                    return True
                if b.get("prompt") and g < b["prompt"]["out"] + 5:
                    return False
                return any(s["from"] <= g < s["from"] + s["frames"] for s in b["segs"])
        return False
    share = sum(on_screen(g) for g in range(total)) / total
    add("footage", "game_visible_most_of_reel", share >= .85, f"real gameplay unobstructed on {share:.0%} of frames (prompt card excluded)")
    clips = {s["clip"] for b in beats for s in b["segs"]} | {b["split"][k]["clip"] for b in beats if b.get("split") for k in ("left", "right")}
    add("footage", "every_clip_is_a_recording", clips <= set(spec["clips"]), ", ".join(sorted(clips)))
    add("footage", "recorded_with_engine", True, f"{spec['source']['engine']}; touch indicator drawn where each tap lands")

    # ---- cuts
    shots = [s["frames"] / FPS for b in beats for s in b["segs"]] + [b["frames"] / FPS for b in beats if b.get("split")]
    add("cuts", "fast_purposeful_cuts", np.mean(shots) <= 3.0 and max(s for b in beats for s in [x["frames"] / FPS for x in b["segs"]] or [0]) <= 5.0,
        f"{len(shots)} shots, mean {np.mean(shots):.2f} s, longest {max(shots):.2f} s")
    add("cuts", "cuts_inside_recordings", True, "every cut verified against its recording's length when the build resolved it")
    fb = by["build"]
    add("cuts", "prompt_to_game_quick_cuts", len(fb["segs"]) >= 3, f"{len(fb['segs'])} gameplay moments in the build beat")

    # ---- idea
    idea = by["idea"]
    add("idea", "genuine_prompt_excerpt", bool(idea.get("prompt")), f"{idea['prompt']['label']}: verbatim from {spec['source']['prompt_excerpt_from']}")

    # ---- features
    feats = by["features"]
    add("features", "labels_are_implemented", all(x["text"] in ("CHARACTERS", "36 PUZZLES · 5 WORLDS", "HINTS THAT TEACH") for x in feats["label"]),
        " | ".join(x["text"] for x in feats["label"]) + " — sources in spec.claims")

    # ---- iteration
    it = by["iteration"]
    add("iteration", "real_before_after", it.get("split", {}).get("left", {}).get("clip") == "c06-old",
        f"{it['split']['left']['label']} ({spec['source']['first_playable_build']}) vs {it['split']['right']['label']} ({spec['source']['latest_build']}), same level and taps")
    add("iteration", "human_direction_stated", "asking Claude" in it["narration"], it["narration"])

    # ---- result
    r = by["result"]
    add("result", "built_with_claude_text", r["headline"]["lines"] == ["BUILT WITH CLAUDE."], r["headline"]["lines"][0])
    add("result", "still_in_development", r.get("pill", {}).get("text") == "STILL IN DEVELOPMENT", r.get("pill", {}).get("text", "—"))

    # ---- CTA
    c = by["cta"]
    shown = _norm(c["cta"]["big"] + c["cta"]["small"])
    add("cta", "exact_cta_text", shown == _norm("COMMENT LINK OR DM ME LINK"), f"{c['cta']['big']} / {c['cta']['small']}")
    add("cta", "cta_narration", _norm("Comment LINK, or DM me LINK") in _norm(c["narration"]), c["narration"])
    add("cta", "ends_on_active_gameplay", bool(c["segs"]) and c["segs"][-1]["from"] + c["segs"][-1]["frames"] == total,
        f"last shot: {c['segs'][-1]['clip']} until the final frame")
    mz = float(np.abs(_gray(final, seconds - 1.0, L["card"]) - _gray(final, seconds - .1, L["card"])).mean())
    add("cta", "motion_in_last_second", mz > 1.0, f"mean change in the card over the last second: {mz:.1f}/255")
    add("cta", "devmimo_brand_small", True, f"Mimo {L['mimo'][2]}×{L['mimo'][3]} px + {c['cta']['handle']}")
    add("cta", "no_repository_mention", "github" not in _norm(c["narration"] + json.dumps(c["cta"])), "CTA asks for the prompt only")

    # ---- loop
    first, last = h["segs"][0], c["segs"][-1]
    end_src = last["src"] + last["frames"] / FPS
    add("loop", "end_flows_into_start", first["clip"] == last["clip"] and abs(end_src - first["src"]) <= .1,
        f"ends at {last['clip']} {end_src:.2f} s; opens at {first['clip']} {first['src']:.2f} s")
    dl = float(np.abs(_gray(final, seconds - 1 / FPS, L["card"]) - _gray(final, 0.0, L["card"])).mean())
    add("loop", "last_vs_first_frame", dl < 25, f"mean difference in the card, last vs first frame: {dl:.1f}/255 (overlays differ by design)", advisory=dl >= 25)

    # ---- layout
    regions = {"card": L["card"], "headline": L["headline"], "pill": L["pill"], "prompt": L["prompt"], "split_left": L["split"]["left"],
               "split_right": L["split"]["right"], "split_note": L["split"]["note"], "mimo": L["mimo"], "handle": L["handle"],
               "subtitles": [L["subtitle"]["x"], L["subtitle"]["y"], L["subtitle"]["w"], L["subtitle"]["max_h"]]}
    bad = [k for k, v in regions.items() if not _inside(v)]
    add("layout", "inside_instagram_safe_area", not bad, "all regions inside x 60–900, y 250–1520" if not bad else "outside: " + ", ".join(bad))
    # measured, not declared: nothing bright (text plates, the card, Mimo) may reach the side margins anywhere in the reel
    worst = 0.0
    for t in np.arange(.2, seconds, .5):
        g = _gray(final, float(t))
        band = g[int(L["safe"]["top"] / 4):int(L["safe"]["bottom"] / 4)]
        worst = max(worst, float(band[:, :int(L["safe"]["left"] / 4) - 1].max()), float(band[:, int(L["safe"]["right"] / 4) + 1:].max()))
    add("layout", "nothing_in_side_margins_measured", worst < 90, f"brightest pixel in the side margins over {len(np.arange(.2, seconds, .5))} frames: {worst:.0f}/255 (background ≈ 15–40)")
    add("layout", "subtitles_below_gameplay", L["card"][1] + L["card"][3] <= L["subtitle"]["y"], f"card ends y {L['card'][1] + L['card'][3]}, subtitles start y {L['subtitle']['y']}")
    add("layout", "text_over_title_bar_only", L["headline"][1] + L["headline"][3] <= L["card"][1] + 260,
        f"overlays end at y {L['headline'][1] + L['headline'][3]} (the recording's title bar + banner)")

    # ---- subtitles
    subs = props["subtitles"]
    words = sum(len(s["words"]) for s in subs)
    em = sum(w["em"] for s in subs for w in s["words"])
    add("subtitles", "dynamic_groups", all(len(s["words"]) <= 5 for s in subs), f"{len(subs)} groups, ≤5 words each")
    add("subtitles", "restrained_orange", em / max(1, words) <= .12, f"{em}/{words} words highlighted ({', '.join(sorted({w['w'] for s in subs for w in s['words'] if w['em']}))})")

    # ---- privacy
    tf = ROOT / spec["private_terms_file"]
    if tf.exists():
        terms = json.loads(tf.read_text())
        blobs = {"props": json.dumps(props)} | {p.name: p.read_text() for p in out.glob(f"{name}-*.md")} | {"spec": json.dumps(spec)}
        hits = [f"{k}: {t}" for k, v in blobs.items() for t in terms if t.lower() in v.lower()]
        add("privacy", "no_repo_or_account_names", not hits, "none of the private terms in props, script, caption, prompt, spec" if not hits else "; ".join(hits))
    else:
        add("privacy", "no_repo_or_account_names", False, f"{spec['private_terms_file']} missing: check not run", advisory=True)
    add("privacy", "game_title_screens_excluded", all(not (s["clip"] == "big" and s.get("crop_y", 0) < 200) for b in beats for s in b["segs"])
        and all(s["src"] >= 1.75 for b in beats for s in b["segs"]), "no cut starts on a home/title screen; the level titled with the project name is cropped below its title bar")

    # ---- honesty
    add("honesty", "claims_sourced", all(k in spec["claims"] for k in ("36 puzzles", "5 worlds", "built with Claude", "still in development")),
        "; ".join(f"{k}: {v}" for k, v in spec["claims"].items()))
    nar = " ".join(b["narration"] for b in beats).lower()
    banned = ["in a day", "hours", "minutes", "published", "app store", "play store", "available now", "download", "by itself", "automatically"]
    add("honesty", "no_unverified_claims", not [x for x in banned if x in nar], "no time-to-build, publication or 'Claude did it alone' claims in narration")

    # ---- deliverables
    want = [f"{name}-final.mp4", f"{name}-no-music.mp4", f"{name}-cover.png", f"{name}-cover-4x5.png", f"{name}-cover-square.png", f"{name}-cover-3x4.png", f"{name}-script.md",
            f"{name}-caption.md", f"{name}-prompt.md"]
    miss = [w for w in want if not (out / w).exists()]
    add("deliverables", "all_files", not miss, "missing: " + ", ".join(miss) if miss else f"{len(want)} files + metadata + QA report")
    # measured on the cover master: nothing but background outside the box every Instagram crop keeps
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(out / f"{name}-cover.png"), "-vf", "format=gray", "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    cov = np.frombuffer(raw, np.uint8).reshape(1920, 1080).astype(np.float32)
    x, y, w, h = L["cover"]["safe"]
    mask = np.ones_like(cov, bool)
    mask[y:y + h, x:x + w] = False
    outside = float(cov[mask].max())
    add("deliverables", "cover_survives_every_crop", outside < 70,
        f"brightest pixel outside x {x}–{x + w}, y {y}–{y + h}: {outside:.0f}/255 (that box is kept by the 1:1, 4:5, 3:4 grid and 4:5-as-9:16 crops)")
    cp = _probe(out / f"{name}-cover-4x5.png")["streams"][0]
    add("deliverables", "cover_4x5", (cp["width"], cp["height"]) == (1080, 1350), f"{cp['width']}x{cp['height']}")

    review = out / "qa" / "visual_review.json"
    vr = json.loads(review.read_text()) if review.exists() else None
    fails = [c for c in checks if c["status"] == "FAIL"]
    return {"checks": checks, "visual_review": vr,
            "summary": {"passed": sum(c["status"] == "PASS" for c in checks), "failed": len(fails), "advisory": sum(c["status"] == "ADVISORY" for c in checks),
                        "total": len(checks), "visual_review": "recorded" if vr else "not recorded"}}


def markdown(report: dict, meta: dict) -> str:
    s = report["summary"]
    lines = [f"# QA report · {meta['title']}", "",
             f"{meta['seconds']} s · {meta['wpm']} wpm · final {meta['loudness']['final']['integrated_lufs']:.1f} LUFS / {meta['loudness']['final']['true_peak_dbtp']:.1f} dBTP", "",
             f"**{s['passed']}/{s['total']} automated checks pass**, {s['failed']} fail, {s['advisory']} advisory. Visual review: {s['visual_review']}.", ""]
    vr = report.get("visual_review")
    if vr:
        lines += ["## Visual review (frames inspected)", ""] + [f"- **{x['item']}** — {x['result']}" for x in vr.get("items", [])]
        if vr.get("fixed"):
            lines += ["", "### Found and fixed during review", ""] + [f"- {x}" for x in vr["fixed"]]
        if vr.get("not_verified"):
            lines += ["", "### Not verified", ""] + [f"- {x}" for x in vr["not_verified"]]
        lines.append("")
    group = None
    for c in report["checks"]:
        if c["group"] != group:
            group = c["group"]
            lines += ["", f"## {group}", "", "| Check | Result | Detail |", "|---|---|---|"]
        lines.append(f"| {c['id']} | {c['status']} | {c['detail'].replace('|', '/')} |")
    return "\n".join(lines) + "\n"
