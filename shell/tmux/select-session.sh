#!/bin/bash
# Switch to the N-th session (1-indexed) in session_id numeric order.
# This matches the order used by cycle-session.sh and the tmux-power status bar.
# Usage: select-session.sh <N>

INDEX="${1:-}"
case "$INDEX" in
  ''|*[!0-9]*) exit 0 ;;
esac

TARGET_NAME=$(tmux list-sessions -F '#{session_id}|#{session_name}' \
  | sed 's/^\$//' \
  | awk -F'|' -v idx="$INDEX" '$1==idx{print $2; exit}')

[ -z "$TARGET_NAME" ] && tmux display-message "no session: $INDEX" && exit 0

tmux switch-client -t "$TARGET_NAME"
