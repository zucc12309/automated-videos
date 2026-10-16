#!/bin/zsh
set -eu
cd "${0:A:h}"
export PATH="/opt/homebrew/bin:/usr/bin:/bin:/Users/priyanshupatel/.nvm/versions/node/v20.20.2/bin:$PATH"
export HF_HUB_DISABLE_TELEMETRY=1
export TOKENIZERS_PARALLELISM=false
# Optional provider credentials (ANTHROPIC_API_KEY, HF_KEY, ...) live in .env, which git ignores. See .env.example.
if [[ -f .env ]]; then set -a; source ./.env; set +a; fi
exec .venv/bin/python -m video_mcp.server
