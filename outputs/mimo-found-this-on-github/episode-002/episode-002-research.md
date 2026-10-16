# EP. 002 research · REA (Reverse Engineer Anything)

Mimo Found This on GitHub · repository: https://github.com/morluto/rea · researched and verified 2026-10-16.

## The two projects in this episode (kept separate on screen)

| | ArtCraft (the hook) | REA (the discovery) |
|---|---|---|
| What | Seven open-source desktop/web apps, each described by its README as a *clean-room reimplementation* of an Adobe app | An MCP server + CLI that lets AI coding agents inspect software: binaries, JS/Electron apps, .NET, APKs, websites, process behaviour |
| Where | github.com/storytold/{photocraft, filmcraft, vectorcraft, effectcraft, lightcraft, designcraft, printcraft} | github.com/morluto/rea · npm `rea-agents` |
| Licence | MIT OR Apache-2.0 (code and README screenshots); ArtCraft name/logos are trademarks (not used in the reel) | MIT |
| Relationship | **None established.** ArtCraft says its apps are clean-room work; nothing says REA was used to build them. Press coverage sometimes puts both in the same headline, which is why the reel labels REA “A DIFFERENT PROJECT”. | |

### The seven Adobe-style apps (verified in each repository's README, commit in brackets)

| Recreation | Modelled on | Commit |
|---|---|---|
| PhotoCraft | Photoshop | 2a952f1 |
| FilmCraft | Premiere Pro | 09aaf9b |
| VectorCraft | Illustrator | 8bc6532 |
| EffectCraft | After Effects | 8f02f52 |
| LightCraft | Lightroom | f34c7a8 |
| DesignCraft | InDesign | c2609f9 |
| PdfCraft (repo `printcraft`; `pdfcraft` redirects) | Acrobat | 9e5b70d |

**“Rebuilt with AI?”** The repositories do not say how much was AI-written. Press reports (PetaPixel 2026-10-07; Notebookcheck; TechRepublic) quote the developer, Brandon Thomas, saying he used Anthropic's Claude to write the apps, and every repo ships `AGENTS.md` / `CLAUDE.md` guides for AI agents. The hook keeps a question mark and the narration says “using AI”, which is what the developer has said. The apps are alpha software; coverage notes the developer's feature-parity claims changed and some users report missing basics. The reel makes no quality or parity claim.

**Screenshots used** (all from the repos' own `docs/images/`, MIT OR Apache-2.0 per NOTICE / ATTRIBUTION.md; the artwork inside them is public domain: Hokusai, NASA Apollo frames, Ansel Adams): photocraft-demo, photocraft-layer-styles, filmcraft-hero, vectorcraft shot-1-neon and shot-6-revolve, effectcraft-hero and -3d, lightcraft hero-tetons, designcraft ui-spread, pdfcraft-viewer. No Adobe screenshots, icons or logos are shown. ArtCraft logos are not shown.

## REA: what was checked

- **Repository**: morluto/rea at 5eaef92 (README, DISCLAIMER.md, LICENSE, package.json). Package `rea-agents` 6.5.0 installed from npm.
- **Environment**: Ubuntu 24.04 container, Node 22.22.0 (REA needs ≥ 22.19), GNU objdump. Hopper / Ghidra / IDA not installed (`rea doctor` reports them missing), so this run used REA's objdump provider and process capture only.
- **MCP**: `rea --mcp` answered `initialize` and `tools/list` with 207 tools.

## The proof: a real, reproducible REA investigation

1. **Target.** The pipeline wrote a small C image filter (`mystery-filter`), compiled it with `gcc -O2 -s` (stripped ELF, sha256 `fa577326…632c`), ran it once on a 600×600 crop of NASA's *Blue Marble* (public domain, taken from LightCraft's README screenshot), and **deleted the source** before the investigation began.
2. **Investigator.** A separate AI agent (a Claude subagent with no access to the source or to this conversation) got the binary, the input image and an MCP client that launches `rea --mcp` and logs every JSON-RPC message. It was told to use REA only and to derive the logic from the disassembly, not by curve-fitting outputs.
3. **REA calls, in order** (raw transcript sha256 `836071be…c886`, trimmed copy in `evidence/episode-002-rea/transcript-trimmed.jsonl`):
   - `capture_process_scenario`: ran the app; exit 0; output `filtered 600x600 (13600 px locked)`.
   - `inspect_with_objdump` `disassemble`: the per-pixel loop at 0x1290–0x1334.
   - `inspect_with_objdump` `section_headers`, then `disassemble_all` (to read the format strings).
4. **Findings** (agent's words, `findings.md`): luma = 77R + 150G + 29B; if luma ≥ 233 the pixel becomes cream (248, 240, 228) and is counted as “locked”; otherwise R' = min(255, (228R + 28G)/256 + 24), G' = (24R + 216G)/256 + 10, B' = (176B + 40·luma)/256 + 4.
5. **Rebuild.** The agent wrote `rebuild.py` (Python stdlib) from those findings. Its output vs. the original binary's output: **0 of 1,080,015 bytes differ** (both sha256 `71d30378…c74c1f`). Checked again independently with `cmp` after the agent finished.

What this does and does not show: REA let an agent understand and reproduce **one specific behaviour** of a small stripped binary without its source. It is not evidence that REA can recreate whole applications, and the test app was made by us, not third-party software. On screen: “REAL REA RUN · TEST APP MADE FOR THIS DEMO” and “NOT A ONE-CLICK CLONER”.

## Claims in the narration → evidence

| Line | Evidence |
|---|---|
| “Someone recreated seven Adobe-style apps using AI.” | Seven README taglines above; developer's statements in press (AI) |
| “Photoshop. Premiere. Illustrator. Even After Effects.” | PhotoCraft, FilmCraft, VectorCraft, EffectCraft READMEs; each screen is labelled with the recreation's own name and “-style · open source” |
| “And people are rebuilding more software every day.” | General framing over the seven-app grid; no numbers claimed |
| “I found a GitHub project called Reverse Engineer Anything.” | README title |
| “Connect it to an AI coding agent, and it can investigate how software works, even without the original source code.” | This episode's run (MCP calls by an agent; stripped binary; source deleted). README lists Claude Code, Codex, Cursor, Gemini CLI |
| “It can inspect code, trace behavior, and help recreate specific features.” | inspect: objdump disassembly (run); trace: `trace`, `trace-application-feature` commands (source / `--help`, not run here) and process capture (run); recreate: byte-identical rebuild (run) |
| “What app would you reverse engineer?” | Question, no claim |

## Responsible-use framing

REA's DISCLAIMER.md: the project does not support circumventing DRM or licence checks, copying proprietary software, or reproducing protected code and assets. The reel avoids “clone any app”, “free Adobe”, “copy software in seconds”. The CTA asks what app the viewer would *reverse engineer / rebuild*; the caption calls REA “not a magic app cloner”.

## Not included

No GitHub stars, forks, downloads, contributor counts, trending ranks or engagement predictions (press quotes star counts for REA; the series never repeats them).

## Hook variants (same facts)

- **A · Curiosity**: “Someone recreated seven Adobe-style apps using AI.” Real screenshots from frame 0 and a two-line headline.
- **B · Contrarian**: “People are rebuilding software that used to take entire teams to make.” Framing, not a measured comparison; no team sizes are quoted for Adobe or ArtCraft.
- **C · Discovery**: “There's a GitHub project that helps AI figure out how apps work.” Opens on REA's official screenshot and then the investigated app.

## Sources

- https://github.com/morluto/rea (README, DISCLAIMER.md, LICENSE; commit 5eaef92) · https://www.npmjs.com/package/rea-agents (6.5.0)
- https://github.com/storytold/photocraft · /filmcraft · /vectorcraft · /effectcraft · /lightcraft · /designcraft · /printcraft
- https://petapixel.com/2026/10/07/someone-rebuilt-free-open-source-versions-of-photoshop-premiere-and-lightroom-using-ai/
- https://www.notebookcheck.net/Photoshop-Premiere-more-Experienced-Rust-developer-recreates-Adobe-suite-with-AI-assistance-as-open-source.1419230.0.html
- https://www.techrepublic.com/article/news-developer-ai-free-adobe-creative-cloud-alternatives/
- Coverage of REA alongside ArtCraft that keeps them distinct: https://www.developersdigest.tech/blog/reverse-engineer-anything-rea-mcp-agents-guide-2026 (search summary; the page itself was not reachable from the build environment)
- Run evidence: `series/mimo-found-this-on-github/evidence/episode-002-rea/` (findings.md, findings-short.json, rebuild.py, disasm-main-loop.txt, transcript-trimmed.jsonl)
