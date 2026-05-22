#!/bin/bash
# Rename the current tmux window to "reponame:branch-tail" (last segment after slash)
# or just "dirname" if not in a git repository.
# Existing emoji prefixes (Claude ✴️, Gemini 💎, etc.) are preserved.
#
# Usage: rename-window-git.sh <path>

# Resolve symlink to find actual script location (tmux_emoji.py lives alongside this script)
_REAL="$(readlink "$0" 2>/dev/null)"
[ -z "$_REAL" ] && _REAL="$0"
SCRIPT_DIR="$(cd "$(dirname "$_REAL")" && pwd)"
TARGET_PATH="${1:-$PWD}"

# Capture current window name and extract emoji prefix before cd changes context
CURRENT_NAME=$(tmux display-message -p "#W" 2>/dev/null)
EMOJI_PREFIX=""
if [ -n "$CURRENT_NAME" ]; then
  STRIPPED=$(python3 "${SCRIPT_DIR}/tmux_emoji.py" "$CURRENT_NAME" 2>/dev/null)
  if [ $? -eq 0 ] && [ -n "$STRIPPED" ]; then
    EMOJI_PREFIX="${CURRENT_NAME%"$STRIPPED"}"
  fi
fi

cd "$TARGET_PATH" || exit 1

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)

if [ -z "$REPO_ROOT" ]; then
  tmux rename-window "${EMOJI_PREFIX}$(basename "$TARGET_PATH")"
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
  tmux rename-window "${EMOJI_PREFIX}${REPO_NAME}"
  exit 0
fi

# Extract the last segment after the final slash
ABBREV="${BRANCH##*/}"

# Truncate if it exceeds 20 chars
if [[ "${#ABBREV}" -gt 20 ]]; then
  ABBREV="${ABBREV:0:20}…"
fi

tmux rename-window "${EMOJI_PREFIX}${REPO_NAME}:${ABBREV}"
