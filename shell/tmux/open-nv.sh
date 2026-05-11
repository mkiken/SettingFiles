#!/bin/bash
# Open nv in a tmux popup from the current git repository root when possible.
# Usage: open-nv.sh <pane_current_path>

TARGET_PATH="${1:-$PWD}"

if [ ! -d "$TARGET_PATH" ]; then
  TARGET_PATH="$PWD"
fi

REPO_ROOT=$(git -C "$TARGET_PATH" rev-parse --show-toplevel 2>/dev/null)

if [ -n "$REPO_ROOT" ]; then
  TARGET_PATH="$REPO_ROOT"
fi

tmux display-popup -d "$TARGET_PATH" -w 90% -h 90% -E "zsh -lc 'exec nvim'"
