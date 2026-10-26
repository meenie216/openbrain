#!/usr/bin/env bash
# Prints Open Brain scope keys for a directory. See README.md's "Scopes".
#
#   scope.sh [DIR]            the project key: the git remote normalised to
#                             owner/repo, falling back to a ~-relative (or
#                             absolute) path. Nothing for $HOME or /tmp
#                             themselves (global only).
#   scope.sh --layers [DIR]   every scope that applies, one per line, general
#                             to specific: the group (if DIR is under a path
#                             listed in the groups file), then the project.
#                             Global is implicit and not printed.
#
# The groups file (OPENBRAIN_GROUPS_FILE, default
# ~/.config/openbrain/groups) has one "<path> <group>" per line, e.g.
#   ~/dev.cm        cm
#   ~/dev.personal  personal
# Blank lines and #-comments are ignored; no file means no groups.
#
# Shared by cli/session-rules.sh (the SessionStart hook) and
# cli/brain-capture, so they can't drift apart.
set -euo pipefail

layers=0
if [ "${1:-}" = "--layers" ]; then
    layers=1
    shift
fi

dir="${1:-$PWD}"
# Resolve symlinks/relative bits so worktrees and clones checked out at
# different paths, or invoked via a relative path, still normalise the
# same way. Falls back to the raw input if the directory doesn't exist.
dir="$(cd "$dir" 2>/dev/null && pwd -P || printf '%s' "$dir")"

group() {
    local file="${OPENBRAIN_GROUPS_FILE:-$HOME/.config/openbrain/groups}"
    [ -r "$file" ] || return 0
    local path name
    while read -r path name _; do
        case "$path" in ''|'#'*) continue ;; esac
        [ -n "$name" ] || continue
        path="${path/#\~/$HOME}"
        path="${path%/}"
        case "$dir" in
            "$path"|"$path"/*) printf '%s\n' "$name"; return 0 ;;
        esac
    done < "$file"
}

project() {
    if [ "$dir" = "$HOME" ] || [ "$dir" = "/tmp" ]; then
        return 0
    fi

    local remote
    remote="$(git -C "$dir" remote get-url origin 2>/dev/null || true)"
    if [ -n "$remote" ]; then
        # git@host:owner/repo.git or https://host/owner/repo.git -> owner/repo.
        # A worktree shares its main clone's remotes, so this gives worktrees
        # the same key as the repo they belong to.
        printf '%s\n' "$remote" | sed -E 's#^.*[:/]([^/]+/[^/]+)$#\1#; s#\.git$##'
        return 0
    fi

    case "$dir" in
        "$HOME"/*) printf '~%s\n' "${dir#"$HOME"}" ;;
        *) printf '%s\n' "$dir" ;;
    esac
}

if [ "$layers" = 1 ]; then
    group
fi
project
