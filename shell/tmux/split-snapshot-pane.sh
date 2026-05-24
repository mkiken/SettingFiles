#!/bin/bash
# Open a split pane with a fixed snapshot of another pane's scrollback.

set -euo pipefail

direction="${1:-}"
target_pane="${2:-}"
pane_path="${3:-$HOME}"

case "$direction" in
  h)
    split_flag="-h"
    ;;
  v)
    split_flag="-v"
    ;;
  *)
    tmux display-message "snapshot split: direction must be h or v"
    exit 2
    ;;
esac

if [[ -z "$target_pane" ]]; then
  tmux display-message "snapshot split: target pane is empty"
  exit 2
fi

if [[ ! -d "$pane_path" ]]; then
  pane_path="$HOME"
fi

tmpfile="$(mktemp "${TMPDIR:-/tmp}/tmux-snapshot.XXXXXX")"
cleanup() {
  /bin/rm -f -- "$tmpfile"
}
trap cleanup EXIT

tmux capture-pane -epS - -t "$target_pane" > "$tmpfile"

printf -v quoted_tmpfile "%q" "$tmpfile"
tmux split-window -d "$split_flag" -t "$target_pane" -c "$pane_path" "LESS= less -R +G -- $quoted_tmpfile; /bin/rm -f -- $quoted_tmpfile"

trap - EXIT
