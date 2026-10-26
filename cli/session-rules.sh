#!/usr/bin/env bash
# Claude Code SessionStart hook: prints Open Brain's standing rules
# (global, plus this directory's group and project scopes if any) as markdown,
# which Claude Code adds to the session's context.
#
# Fails open, always exiting 0: an unreachable Open Brain, a missing or
# rejected token, or anything else wrong here should never block a
# session starting — it should just mean today's session runs without
# standing rules, with a one-line warning on stderr saying so.
# Deliberately not `set -e`: a function called as `main || warn` is run
# with errexit ignored throughout its body (that's POSIX/bash's own
# documented behaviour for a command tested by ||, and it applies to
# everything inside, not just the top-level call) — so every step below
# checks its own exit status explicitly with `|| return 1` instead.
set -uo pipefail

TOKEN_FILE="${OPENBRAIN_READ_TOKEN_FILE:-$HOME/.config/openbrain/read-token}"
# The URL comes from the environment, or from the env file brain-capture users
# already keep (read with sed, not sourced, so the write token in it never
# enters this process). Hooks can start without a login shell's environment.
ENV_FILE="${OPENBRAIN_ENV_FILE:-$HOME/.config/openbrain/env}"
if [ -z "${OPENBRAIN_CAPTURE_URL:-}" ] && [ -r "$ENV_FILE" ]; then
    OPENBRAIN_CAPTURE_URL="$(sed -n 's/^export OPENBRAIN_CAPTURE_URL=//p' "$ENV_FILE")"
fi
BASE_URL="${OPENBRAIN_CAPTURE_URL:-http://localhost:8080}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

main() {
    local token cwd scope url response query

    token="$(cat "$TOKEN_FILE" 2>/dev/null)" || return 1
    [ -n "$token" ] || return 1

    # Claude Code's SessionStart hook input is JSON on stdin with a `cwd`
    # field; fall back to $PWD if that's missing or unparseable, rather
    # than failing the whole hook over it.
    cwd="$(jq -r '.cwd // empty' 2>/dev/null)" || cwd=""
    [ -n "$cwd" ] || cwd="$PWD"

    # One scope per line (group, then project), general to specific; sent as
    # repeated scope= params. None means global rules only.
    query=""
    while IFS= read -r scope; do
        [ -n "$scope" ] || continue
        query="$query&scope=$(jq -rn --arg s "$scope" '$s|@uri')" || return 1
    done < <("$SCRIPT_DIR/scope.sh" --layers "$cwd")
    url="$BASE_URL/rules?${query#&}"

    response="$(curl -sf --max-time 3 -H "Authorization: Bearer $token" "$url")" || return 1
    printf '%s\n' "$response"
}

main || echo "Open Brain unreachable — standing rules not loaded" >&2
exit 0
