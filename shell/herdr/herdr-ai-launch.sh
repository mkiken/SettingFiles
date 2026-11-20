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

# CLIがAIとして検出される前の agent wait は agent_not_found で即失敗する。
# 検出されるまで再試行し、検出後の入力待ちは herdr 側のタイムアウトに任せる。
# pane runの末尾欠落でCLIが起動しなかった場合も、検出されないままここで失敗する。
# blocked（起動時の確認ダイアログ等）は待ち条件に含めず、そこへは送信しない。
# 待ち時間の環境変数はテストが待ちを潰すための上書き用（既定は本番値）。
poll_interval="${HERDR_AI_LAUNCH_POLL_INTERVAL:-0.3}"
detect_seconds="${HERDR_AI_LAUNCH_DETECT_SECONDS:-30}"
detect_start=$SECONDS
while true; do
  if wait_out=$(herdr agent wait "$new" --until idle --until done --timeout 60000 2>&1); then
    break
  fi
  code=$(jq -r '.error.code // empty' <<<"$wait_out" 2>/dev/null || true)
  if [[ "$code" != "agent_not_found" ]] || (( SECONDS - detect_start >= detect_seconds )); then
    detail=$(jq -r '(.error // {}) | "\(.code // "unknown"): \(.message // "")"' <<<"$wait_out" 2>/dev/null || echo "$wait_out")
    echo "herdr ai launch: ${command} の入力待ちを確認できませんでした (pane_id=${new}): ${detail}" >&2
    exit 1
  fi
  sleep "$poll_interval"
done

echo "$new"
