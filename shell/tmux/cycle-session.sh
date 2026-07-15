#!/bin/bash
# Cycle to next/previous tmux session in the same order as @session_shortcut_index
# (list-sessions -O index order), matching the status bar / select-session.sh.
# Usage: cycle-session.sh [next|prev]

DIR="${1:-next}"

CUR_ID=$(tmux display-message -p '#{session_id}')

# list-sessions -O index is the same ordering sync-session-shortcuts.sh uses
# to assign @session_shortcut_index, so this matches the footer order.
LIST=$(tmux list-sessions -O index -F '#{session_id}|#{session_name}')

COUNT=$(printf '%s\n' "$LIST" | wc -l | tr -d ' ')
[ "$COUNT" -le 1 ] && tmux display-message "no other session" && exit 0

IDX=$(printf '%s\n' "$LIST" | awk -F'|' -v cur="$CUR_ID" '$1==cur{print NR; exit}')
[ -z "$IDX" ] && exit 0

if [ "$DIR" = "prev" ]; then
  NEW=$(( IDX - 1 ))
  [ "$NEW" -lt 1 ] && NEW="$COUNT"
else
  NEW=$(( IDX + 1 ))
  [ "$NEW" -gt "$COUNT" ] && NEW=1
fi

NEW_NAME=$(printf '%s\n' "$LIST" | sed -n "${NEW}p" | cut -d'|' -f2)
tmux switch-client -t "$NEW_NAME"
