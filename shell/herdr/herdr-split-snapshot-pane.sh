#!/bin/bash

# Herdrで現在ペインのスナップショットを分割ペインのlessに表示する。
# config.tomlのprefix+ctrl+s/ctrl+vから呼ばれる（インラインbashだと
# TOML多層クォートが誤りやすいためスクリプトに分離）。
# 引数: direction (down | right)

set -euo pipefail

direction="${1:-}"

case "$direction" in
  down|right) ;;
  *)
    echo "herdr snapshot split: direction must be down or right" >&2
    exit 2
    ;;
esac

# popup/keys.command環境ではHERDR_PANE_IDは使えず、発火元ペインはHERDR_ACTIVE_PANE_ID
src="${HERDR_ACTIVE_PANE_ID:-}"
if [[ -z "$src" ]]; then
  echo "herdr snapshot split: HERDR_ACTIVE_PANE_ID is empty" >&2
  exit 2
fi

out=$(herdr pane split --pane "$src" --direction "$direction" --ratio 0.5 --focus)
new=$(jq -r '.result.pane.pane_id' <<<"$out")
if [[ -z "$new" || "$new" == "null" ]]; then
  echo "herdr snapshot split: pane split結果からpane_idを取得できませんでした" >&2
  exit 1
fi

source "$(dirname "$0")/herdr_wait_shell_ready.sh"
_herdr_wait_shell_ready "$new" || exit 1

herdr pane run "$new" "herdr pane read $src --source recent --lines 5000 --format text | less -R +G"
