#!/bin/bash
# Create or attach to a tmux session.
# If $1 is empty, derive name from git repo/branch at $2 (pane current path).
# Usage: new-session.sh <name> <pane_current_path>

NAME="${1}"
PANE_PATH="${2:-$PWD}"

if [ -z "$NAME" ]; then
  cd "$PANE_PATH" 2>/dev/null || cd "$HOME"
  REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
  if [ -n "$REPO_ROOT" ]; then
    REPO_NAME=$(basename "$REPO_ROOT")
    BRANCH=$(git branch --show-current 2>/dev/null)
    DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null)
    DEFAULT_BRANCH="${DEFAULT_BRANCH##refs/remotes/origin/}"
    if [ -n "$BRANCH" ] && [ "$BRANCH" != "$DEFAULT_BRANCH" ]; then
      NAME="${REPO_NAME}-${BRANCH##*/}"
    else
      NAME="$REPO_NAME"
    fi
  else
    NAME=$(basename "$PANE_PATH")
  fi
fi

# tmux session names: '.' and ':' are not allowed
NAME="${NAME//:/_}"
NAME="${NAME//./_}"

if ! tmux has-session -t="$NAME" 2>/dev/null; then
  tmux new-session -d -s "$NAME" -c "$PANE_PATH"
fi
tmux switch-client -t "$NAME"
