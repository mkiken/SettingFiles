#!/bin/bash

# nvim の herdr_ai.lua から呼ばれ、元ペインの右に AI CLI のペインを作って起動する。
# 起動したCLIが入力待ち(idle)になるまで待ち、成功時のみ新ペインIDをstdoutへ出す。
# 引数: src_pane_id cwd command
#   command は新ペインの対話zshで実行されるため、エイリアス/関数（clo, cxa, gmf 等）が使える。

set -euo pipefail

if [[ $# -ne 3 || -z "$1" || -z "$3" ]]; then
  echo "usage: herdr-ai-launch.sh <src_pane_id> <cwd> <command>" >&2
  exit 2
fi

src="$1"
cwd="$2"
command="$3"

out=$(herdr pane split --pane "$src" --direction right --ratio 0.5 --focus --cwd "$cwd")
new=$(jq -r '.result.pane.pane_id // empty' <<<"$out")
if [[ -z "$new" ]]; then
  echo "herdr ai launch: pane split結果からpane_idを取得できませんでした" >&2
  exit 1
fi

source "$(dirname "$0")/herdr_wait_shell_ready.sh"
_herdr_wait_shell_ready "$new" || exit 1

herdr pane run "$new" "$command" >/dev/null

# pane runの末尾欠落でCLIが起動しなかった場合もここで検出する
if ! herdr agent wait "$new" --until idle --timeout 60000 >/dev/null 2>&1; then
  echo "herdr ai launch: ${command} の入力待ちを確認できませんでした (pane_id=${new})" >&2
  exit 1
fi

echo "$new"
