#!/bin/bash
# Cycle to next/previous tmux session in session_id numeric order.
# This matches the status bar order produced by #{S:...} iteration in tmux-power.
# Usage: cycle-session.sh [next|prev]

DIR="${1:-next}"

CUR_ID=$(tmux display-message -p '#{session_id}')
CUR_ID="${CUR_ID#\$}"

# Strip '$' prefix from session_id and sort numerically
LIST=$(tmux list-sessions -F '#{session_id}|#{session_name}' \
  | sed 's/^\$//' \
  | sort -t'|' -k1 -n)

COUNT=$(printf '%s\n' "$LIST" | wc -l | tr -d ' ')
[ "$COUNT" -le 1 ] && exit 0

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
