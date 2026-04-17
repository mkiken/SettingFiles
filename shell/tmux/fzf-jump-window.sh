#!/bin/bash
# Fuzzy-find tmux windows across all sessions and jump to the selected one.
# Preview renders a live snapshot of the window's active pane.

set -euo pipefail

# fzf preview runs in a non-interactive subshell which may not inherit a
# login PATH, so ensure Homebrew paths are visible to `tmux` calls inside it.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

LIST=$(tmux list-windows -a -F $'#{session_name}:#{window_index}\t#{session_name} > #{window_index}: #{window_name} · #{pane_current_path}')
LIST=${LIST//"$HOME"/\~}
[ -z "$LIST" ] && exit 0

PREVIEW='
target={1}
info=$(tmux list-windows -a -f "#{==:#{session_name}:#{window_index},$target}" -F "#{session_name}|#{window_index}|#{window_name}|#{pane_current_path}")
sess=${info%%|*}
rest=${info#*|}
idx=${rest%%|*}
rest=${rest#*|}
win=${rest%%|*}
path=${rest##*|}
path=${path/#$HOME/\~}
printf "\033[1;33mSession\033[0m : %s\n" "$sess"
printf "\033[1;33mWindow \033[0m : %s: %s\n" "$idx" "$win"
printf "\033[1;33mPath   \033[0m : %s\n" "$path"
printf -- "----------------------------------------\n"
tmux capture-pane -ep -t "$target"
'

SELECTED=$(
  printf "%s\n" "$LIST" \
    | SHELL=/bin/bash fzf --ansi \
          --with-nth=2 \
          --delimiter=$'\t' \
          --preview="$PREVIEW" \
          --preview-window='right:60%:wrap' \
          --header='Jump to tmux window' \
          --prompt='window> ' \
          --cycle --exit-0
) || exit 0

TARGET=$(printf "%s" "$SELECTED" | cut -f1)
SESSION=${TARGET%%:*}

tmux switch-client -t "$SESSION"
tmux select-window -t "$TARGET"
