#!/bin/bash
# Open an IDE-owned tmux session without making multiple IDE terminals share
# the same current window.

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
  TMUX= TMUX_PANE= tmux "$@"
}

rename_target_window() {
  local window_id="$1"
  if [ -n "$window_id" ] && [ -x "$RENAME_SCRIPT" ]; then
    TMUX= TMUX_PANE= "$RENAME_SCRIPT" "$PANE_PATH" "$window_id"
  fi
}

attach_session() {
  local session_name="$1"
  TMUX= TMUX_PANE= tmux attach-session -t "=${session_name}"
}

if ! tmux_clean has-session -t "=${BASE_SESSION}" 2>/dev/null; then
  if WINDOW_ID=$(tmux_clean new-session -d -P -F "#{window_id}" -s "$BASE_SESSION" -c "$PANE_PATH" 2>/dev/null); then
    tmux_clean set-option -t "$BASE_SESSION" window-size largest
    rename_target_window "$WINDOW_ID"
    attach_session "$BASE_SESSION"
    exit $?
  fi
fi

CLIENT_SESSION="${BASE_SESSION}-$$"
while tmux_clean has-session -t "=${CLIENT_SESSION}" 2>/dev/null; do
  CLIENT_SESSION="${CLIENT_SESSION}-${RANDOM}"
done

if ! tmux_clean new-session -d -s "$CLIENT_SESSION" -t "=${BASE_SESSION}"; then
  attach_session "$BASE_SESSION"
  exit $?
fi

tmux_clean set-option -t "$CLIENT_SESSION" window-size largest

WINDOW_ID=$(tmux_clean new-window -d -P -F "#{window_id}" -t "${CLIENT_SESSION}:" -c "$PANE_PATH") || {
  tmux_clean kill-session -t "=${CLIENT_SESSION}" 2>/dev/null || true
  exit 1
}

rename_target_window "$WINDOW_ID"
tmux_clean select-window -t "${CLIENT_SESSION}:${WINDOW_ID}"

attach_session "$CLIENT_SESSION"
ATTACH_STATUS=$?
case "$ATTACH_STATUS" in
  ''|*[!0-9]*) ATTACH_STATUS=1 ;;
esac

ATTACHED_COUNT=$(tmux_clean display-message -p -t "${CLIENT_SESSION}:" "#{session_attached}" 2>/dev/null)
if [ "$ATTACHED_COUNT" = "0" ]; then
  tmux_clean kill-session -t "=${CLIENT_SESSION}" 2>/dev/null || true
fi

exit "$ATTACH_STATUS"
