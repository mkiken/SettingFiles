#!/bin/bash
# Open an IDE-owned tmux session scoped to the current repository or worktree.

BASE_SESSION="${1:-}"
PANE_PATH="${2:-$PWD}"

if [ -z "$BASE_SESSION" ]; then
  exit 1
fi

_REAL="$(readlink "$0" 2>/dev/null)"
[ -z "$_REAL" ] && _REAL="$0"
SCRIPT_DIR="$(cd "$(dirname "$_REAL")" && pwd)"
RENAME_SCRIPT="${SCRIPT_DIR}/rename-window-git.sh"

tmux_clean() {
  TMUX='' TMUX_PANE='' tmux "$@"
}

workspace_basename() {
  local repo_root
  repo_root=$(git -C "$PANE_PATH" rev-parse --show-toplevel 2>/dev/null)
  if [ -n "$repo_root" ]; then
    basename "$repo_root"
  else
    basename "$PANE_PATH"
  fi
}

sanitize_session_part() {
  local value="$1"
  value=$(printf '%s' "$value" | LC_ALL=C tr -c '[:alnum:]_-' '_')
  while [[ "$value" == *__* ]]; do
    value="${value//__/_}"
  done
  value="${value#_}"
  value="${value%_}"
  if [ -z "$value" ]; then
    value="workspace"
  fi
  printf '%s' "$value"
}

rename_target_window() {
  local window_id="$1"
  if [ -n "$window_id" ] && [ -x "$RENAME_SCRIPT" ]; then
    TMUX='' TMUX_PANE='' "$RENAME_SCRIPT" "$PANE_PATH" "$window_id"
  fi
}

attach_session() {
  local session_name="$1"
  TMUX='' TMUX_PANE='' tmux attach-session -t "=${session_name}"
}

SAFE_PREFIX=$(sanitize_session_part "$BASE_SESSION")
SAFE_WORKSPACE=$(sanitize_session_part "$(workspace_basename)")
SESSION_NAME="${SAFE_PREFIX}-${SAFE_WORKSPACE}"

if ! tmux_clean has-session -t "=${SESSION_NAME}" 2>/dev/null; then
  if WINDOW_ID=$(tmux_clean new-session -d -P -F "#{window_id}" -s "$SESSION_NAME" -c "$PANE_PATH" 2>/dev/null); then
    tmux_clean set-option -t "$SESSION_NAME" window-size largest
    rename_target_window "$WINDOW_ID"
    attach_session "$SESSION_NAME"
    exit $?
  fi

  attach_session "$SESSION_NAME"
  exit $?
fi

tmux_clean set-option -t "$SESSION_NAME" window-size largest

WINDOW_ID=$(tmux_clean new-window -d -P -F "#{window_id}" -t "${SESSION_NAME}:" -c "$PANE_PATH") || exit 1

rename_target_window "$WINDOW_ID"
tmux_clean select-window -t "$WINDOW_ID"

attach_session "$SESSION_NAME"
