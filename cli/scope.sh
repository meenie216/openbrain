#!/usr/bin/env bash
# Prints the Open Brain project scope key for a directory: the git remote
# normalised to owner/repo, falling back to a ~-relative (or absolute)
# path. Prints nothing for $HOME or /tmp themselves — global rules and
# thoughts only. Shared by cli/session-rules.sh (the SessionStart hook)
# and cli/brain-capture, so they can't drift apart. See
# README.md's "Project key" section.
#
# Usage: scope.sh [DIR]   (defaults to $PWD)
set -euo pipefail

dir="${1:-$PWD}"
# Resolve symlinks/relative bits so worktrees and clones checked out at
# different paths, or invoked via a relative path, still normalise the
# same way. Falls back to the raw input if the directory doesn't exist.
dir="$(cd "$dir" 2>/dev/null && pwd -P || printf '%s' "$dir")"

if [ "$dir" = "$HOME" ] || [ "$dir" = "/tmp" ]; then
    exit 0
fi

remote="$(git -C "$dir" remote get-url origin 2>/dev/null || true)"
if [ -n "$remote" ]; then
    # git@host:owner/repo.git or https://host/owner/repo.git -> owner/repo.
    # A worktree shares its main clone's remotes, so this gives worktrees
    # the same key as the repo they belong to.
    printf '%s\n' "$remote" | sed -E 's#^.*[:/]([^/]+/[^/]+)$#\1#; s#\.git$##'
    exit 0
fi

case "$dir" in
    "$HOME"/*) printf '~%s\n' "${dir#"$HOME"}" ;;
    *) printf '%s\n' "$dir" ;;
esac
