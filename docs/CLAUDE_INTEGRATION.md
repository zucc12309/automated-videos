# Claude integration

## Two paths, deliberately separate

| Path | What it is | Used for |
|---|---|---|
| Interactive development | A person working in Claude Code edits the repo, writes storyboards or components | Authoring storyboards (`examples/demos/storyboard_*.json`), new Remotion components via the component forge |
| Runtime automation | `video_mcp/providers/claude_provider.py` calls the Anthropic Messages API with an API key | Unattended creative direction in CLAUDE / HYBRID jobs |

A Claude.ai / Claude Code subscription is **not** API access. The runtime provider uses only `ANTHROPIC_API_KEY` (or
`ANTHROPIC_AUTH_TOKEN`) and pins the endpoint to `VIDEO_MCP_ANTHROPIC_BASE_URL` or `https://api.anthropic.com`, so it
never inherits an interactive session's `ANTHROPIC_BASE_URL`. Storyboards authored interactively carry
`director.interactive = true` and are never reported as runtime API output.

## Model

* Config alias `creative_director.preferred_claude_model: "opus-5.5"` resolves to the API identifier `claude-opus-5-5`
  (verified against Anthropic's model table cached 2026-10-06). Other aliases: `sonnet-5.5`, `haiku-5.5`. Unknown
  values are passed through as literal model IDs.
* Requests use `output_config.effort` (default `medium`, Opus 5.5's own default) — thinking is always on for this model
  and is not configured. Structured output: `output_config.format = json_schema` built from `DirectorOutput`
  (constraint-free schema; limits are enforced afterwards by Pydantic).
* Server-side refusal fallback is enabled (`betas=["server-side-fallback-2026-07-01"]`, `fallbacks="default"`); the
  model that actually served the request is recorded and priced.
* The director system prompt is byte-stable and marked `cache_control: ephemeral` so repeated jobs hit the prompt cache.

## Request / validation loop

1. Research packet (sources + facts) is neutralized for injection phrases and wrapped in `<research>` tags; the
   system prompt says it is data, never instructions.
2. Response must be `stop_reason == end_turn`; `refusal` and `max_tokens` raise classified errors.
3. JSON → `DirectorOutput` → `Storyboard` (length limits, emphasis/stat must come from the narration, unknown claim and
   scene references dropped, verified claims without sources downgraded).
4. Deterministic grounding checks (numbers absent from the research, missing emphasis, cinematic used for code/UI/data,
   too many cinematic scenes, hook too long). Failures are sent back in an append-only revision turn, up to
   `creative_director.max_revisions`.
5. `research.verify` then maps every narrated sentence to sources and removes unsupported numeric sentences.

## Cost and authorization

Before **every** call `Pipeline.claude_gate` reserves a conservative upper bound
(`input ≈ chars/3 + 500` tokens, output = `max_tokens`) at list price ($4 / $20 per MTok for Opus 5.5, cache reads
$0.20), then reconciles with `usage` (input, output, cache read, cache write). Calls that fail before billing release
the reservation; timeouts keep it. `max_claude_calls_per_video` caps attempts. Claude is called only when:

1. `ANTHROPIC_API_KEY` is set and the `anthropic` package is installed (`pip install -r requirements-claude.lock.txt`),
2. `budget.allow_paid_generation` is true and `approval_policy` is not `deny`,
3. under `explicit`, the job carries an approval (`approved_budget_usd` on `create_hybrid_video`, or `approve_generation`).

Otherwise the job falls back to Ollama → template, and `decisions.json` says why.

## Errors

| Anthropic exception | ProviderError kind | Retry |
|---|---|---|
| RateLimitError (429, `retry-after` parsed) | `rate_limit` | SDK retries ×2; then fallback |
| AuthenticationError / PermissionDeniedError | `auth` | no |
| NotFoundError / BadRequestError | `bad_request` | no |
| APITimeoutError | `timeout` (cost kept) | no blind retry |
| APIConnectionError | `unavailable` | fallback |
| 5xx | `server` | SDK retries; then fallback |

## Status in this delivery

Implemented and tested with a mocked client (success, revision after invalid output and after ungrounded numbers,
rate-limit classification, refusal, base-URL pinning, gate/settle accounting). **No live API call was made**: the build
environment has no API key, and paid calls require your authorization. To run one: set `ANTHROPIC_API_KEY`, set
`budget.allow_paid_generation: true`, then `python examples/demos/demo_b_claude.py --runtime` (approves $0.90).
