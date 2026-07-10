#!/bin/bash
# Assign dense zero-based shortcut indexes in the same order as the status bar.

LOCK_CHANNEL='settingfiles-sync-session-shortcuts'
tmux wait-for -L "$LOCK_CHANNEL" || exit 0
release_lock() {
  tmux wait-for -U "$LOCK_CHANNEL"
}
trap release_lock EXIT
trap 'exit 1' HUP INT TERM

INDEX=0
while IFS= read -r SESSION_ID; do
  [ -z "$SESSION_ID" ] && continue

  tmux set-option -t "$SESSION_ID" @session_shortcut_index "$INDEX"
  INDEX=$((INDEX + 1))
done < <(tmux list-sessions -O index -F '#{session_id}' 2>/dev/null)
