# EP. 002 · 7 Adobe-style apps rebuilt with AI, and the tool that helps agents understand apps

Mimo Found This on GitHub · repository: https://github.com/morluto/rea
Format: reel-v2 (shock → context → mystery → discovery → proof → possibility → question) · demo status: **captured**

| Beat | Start | Length | Narration | On screen |
|---|---|---|---|---|
| shock | 0.00s | 3.53s | Someone recreated seven Adobe-style apps using AI. | 7 ADOBE APPS. / REBUILT WITH AI? |
| context | 3.53s | 4.17s | Photoshop. Premiere. Illustrator. Even After Effects. | PHOTOCRAFT / FILMCRAFT / VECTORCRAFT / EFFECTCRAFT |
| mystery | 7.70s | 3.47s | And people are rebuilding more software every day. | 7 app grid |
| discovery | 11.17s | 3.60s | I found a GitHub project called Reverse Engineer Anything. | A DIFFERENT PROJECT · MIT |
| proof | 14.77s | 7.40s | Connect it to an AI coding agent, and it can investigate how software works, even without the original source code. | AGENT → REA · MCP / NO SOURCE CODE / exit 0 capture |
| possibility | 22.17s | 5.27s | It can inspect code, trace behavior, and help recreate specific features. | OBSERVE / INVESTIGATE / REBUILD / 0 BYTES DIFFERENT / NOT A ONE-CLICK CLONER / trace behavior |
| question | 27.43s | 4.07s | But imagine what you could build. What app would you reverse engineer? | WHAT APP WOULD YOU REBUILD? / FOLLOW @DEVMIMO |

73 words, 160 wpm while speaking.

## Hook variants

- **A · Curiosity** (4.7s, `episode-002-hook-a.mp4`): “Someone recreated seven Adobe-style apps using AI.” — on screen: 7 ADOBE APPS. / REBUILT WITH AI?
- **B · Contrarian** (5.4s, `episode-002-hook-b.mp4`): “People are rebuilding software that used to take entire teams to make.” — on screen: BIG-TEAM SOFTWARE. / REBUILT WITH AI? — caveat: Framing, not a measured comparison: no team sizes are quoted for Adobe or ArtCraft.
- **C · Discovery** (4.8s, `episode-002-hook-c.mp4`): “There's a GitHub project that helps AI figure out how apps work.” — on screen: HOW DOES AN APP WORK? / ASK REA.

Selected: **A** (see the QA report for the comparison).

## Verified features shown

- **Seven Adobe-style open-source apps** (verified-source): ArtCraft publishes seven open-source apps, each described as a clean-room reimplementation of an Adobe app: PhotoCraft (Photoshop), FilmCraft (Premiere Pro), VectorCraft (Illustrator), EffectCraft (After Effects), LightCraft (Lightroom), DesignCraft (InDesign), PdfCraft (Acrobat). — evidence: README taglines of github.com/storytold/{photocraft,filmcraft,vectorcraft,effectcraft,lightcraft,designcraft,printcraft} at the commits in verification.artcraft_commits; screenshots are the repos' own docs/images (MIT OR Apache-2.0 per NOTICE / ATTRIBUTION.md)
- **Built with AI help (developer's statement)** (verified-source): The developer told reporters he used Anthropic's Claude to write the apps; every repo ships AGENTS.md / CLAUDE.md guides for AI agents. — evidence: PetaPixel 2026-10-07, Notebookcheck, TechRepublic (verification.sources); AGENTS.md and CLAUDE.md in each repo. The repos' READMEs themselves do not state how much was AI-written, so the hook keeps a question mark.
- **Plugs into AI coding agents over MCP** (verified-run): REA runs as an MCP server that AI coding agents call. — evidence: rea --mcp answered initialize + tools/list with 207 tools; an agent then called capture_process_scenario and inspect_with_objdump through it (transcript-trimmed.jsonl). README: setup supports Claude Code, Codex, Cursor, Gemini CLI.
- **Works without the source code** (verified-run): REA inspected a stripped binary whose source had been deleted before the investigation. — evidence: mystery-filter sha256 fa577326…632c, ELF stripped; source removed before the agent started; disasm-main-loop.txt is REA's inspect_with_objdump output
- **Observes what an app does** (verified-run): capture_process_scenario ran the app and recorded its output and exit. — evidence: capture evidence: exit code 0, terminal output 'filtered 600x600 (13600 px locked)' (transcript-trimmed.jsonl, call 1)
- **Inspects compiled code** (verified-run): inspect_with_objdump returned the disassembly the agent read the filter's rules from. — evidence: disasm-main-loop.txt lines 0x1290–0x1334; findings.md cites each address
- **Traces behaviour** (verified-source): REA has commands that trace a feature through analysed references and captured behaviour. — evidence: rea --help: trace, trace-application-feature, trace-javascript-semantics, capture-process (rea-agents 6.5.0). This episode ran capture_process_scenario, not the trace commands.
- **Helps recreate a specific feature** (verified-run): From REA's evidence the agent rewrote the filter; its output matched the original byte for byte. — evidence: rebuild.py; cmp original-out.ppm rebuilt-out.ppm: 0 of 1,080,015 bytes differ (both sha256 71d30378…c74c1f)
- **Not a one-click cloner** (verified-source): REA is an investigation tool; the project does not support copying proprietary software. — evidence: DISCLAIMER.md (Responsible use): 'does not support … copying proprietary software or reproducing its protected code and assets'
- **Open source (MIT)** (verified-source): REA is MIT-licensed. — evidence: LICENSE, package.json license MIT

## Demonstration notes

- Shock / context / mystery beats show ArtCraft's own published screenshots (MIT OR Apache-2.0; artwork in them is public domain), labelled as open-source recreations, not Adobe.
- Proof / possibility beats show a real REA 6.5.0 investigation captured for this episode: a separate AI agent with only a stripped test binary called REA over MCP and rebuilt the filter; outputs compared byte for byte.
- The test app was written by the DevMimo pipeline for this demo (its source was deleted before the investigation); it is not third-party software.
- REA was not used on ArtCraft or on any Adobe product.
