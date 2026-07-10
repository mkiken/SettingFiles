#!/bin/bash
# Switch to the session with the zero-based shortcut shown in the status bar.
# Usage: select-session.sh <index> [client-name]

INDEX="${1:-}"
CLIENT_NAME="${2:-}"
case "$INDEX" in
  ''|*[!0-9]*) exit 0 ;;
esac

TARGET_ID=""
MATCH_COUNT=0
while IFS=$'\t' read -r SESSION_ID SHORTCUT_INDEX; do
  [ "$SHORTCUT_INDEX" != "$INDEX" ] && continue

  TARGET_ID="$SESSION_ID"
  MATCH_COUNT=$((MATCH_COUNT + 1))
done < <(tmux list-sessions -O index \
  -F $'#{session_id}\t#{@session_shortcut_index}' 2>/dev/null)

[ "$MATCH_COUNT" -ne 1 ] && tmux display-message "no session: $INDEX" && exit 0

if [ -n "$CLIENT_NAME" ]; then
  tmux switch-client -c "$CLIENT_NAME" -t "$TARGET_ID"
else
  tmux switch-client -t "$TARGET_ID"
fi
