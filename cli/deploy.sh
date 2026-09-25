#!/usr/bin/env bash
# Syncs code to the machine named by DEPLOY_TARGET (user@host:path/).
# Deliberately excludes .env: it holds host-specific settings
# (OLLAMA_BASE_URL, COMPOSE_PROFILES) alongside values that should sync
# (API keys, bearer tokens), and a wholesale copy has clobbered the target's
# host-specific values with the source's. Any .env change on the target is a
# manual edit, done there, documented in the commit that adds the variable.
set -euo pipefail

: "${DEPLOY_TARGET:?set DEPLOY_TARGET, e.g. user@host:~/openbrain/}"

cd "$(dirname "$0")/.."
rsync -a --itemize-changes \
    --exclude .venv --exclude __pycache__ --exclude .env \
    ./ "$DEPLOY_TARGET"
