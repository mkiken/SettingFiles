#!/bin/bash
# Rename the current tmux window to "reponame:branch-tail" (last segment after slash)
# or just "dirname" if not in a git repository.
#
# Usage: rename-window-git.sh <path>

TARGET_PATH="${1:-$PWD}"

cd "$TARGET_PATH" || exit 1

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)

if [ -z "$REPO_ROOT" ]; then
  tmux rename-window "$(basename "$TARGET_PATH")"
  exit 0
fi

REPO_NAME=$(basename "$REPO_ROOT")
BRANCH=$(git branch --show-current 2>/dev/null)

if [ -z "$BRANCH" ]; then
  # detached HEAD: show short SHA
  BRANCH=$(git rev-parse --short HEAD 2>/dev/null)
fi

# Detect default branch (fast, local-only via symbolic-ref)
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null)
DEFAULT_BRANCH="${DEFAULT_BRANCH##refs/remotes/origin/}"

# On default branch: show repo name only
if [[ -n "${DEFAULT_BRANCH}" ]] && [[ "${BRANCH}" = "${DEFAULT_BRANCH}" ]]; then
  tmux rename-window "${REPO_NAME}"
  exit 0
fi

# Extract the last segment after the final slash
ABBREV="${BRANCH##*/}"

# Truncate if it exceeds 20 chars
if [[ "${#ABBREV}" -gt 20 ]]; then
  ABBREV="${ABBREV:0:20}…"
fi

tmux rename-window "${REPO_NAME}:${ABBREV}"
