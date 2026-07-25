#!/bin/bash
# ランディレクトリに期待する結果ファイルが全て(非空で)揃うまでポーリングして待つ。
# 使い方: ai_review_wait.sh <run_dir> <file...>
# 環境変数: AI_REVIEW_WAIT_INTERVAL(default 5) / AI_REVIEW_WAIT_TIMEOUT(default 7200)
# 終了コード: 0=揃った / 1=引数不正 / 2=タイムアウト
# 進捗表示はstderr(1行上書き)。中断はCtrl-C。

set -u

main() {
    local run_dir="${1:-}"
    if [[ -z "$run_dir" || $# -lt 2 ]]; then
        echo "Usage: ai_review_wait.sh <run_dir> <file...>" >&2
        return 1
    fi
    shift

    local interval="${AI_REVIEW_WAIT_INTERVAL:-5}"
    local timeout="${AI_REVIEW_WAIT_TIMEOUT:-7200}"
    local start_epoch elapsed
    start_epoch=$(date +%s)

    while :; do
        local pending=0 status_line="" f
        for f in "$@"; do
            if [[ -s "${run_dir}/${f}" ]]; then
                status_line+=" ${f%.md} ✓"
            else
                status_line+=" ${f%.md} …"
                pending=1
            fi
        done
        elapsed=$(( $(date +%s) - start_epoch ))
        printf '\r\033[Kレビュー完了待ち:%s (%ds)' "$status_line" "$elapsed" >&2
        if (( pending == 0 )); then
            printf '\n' >&2
            return 0
        fi
        if (( elapsed >= timeout )); then
            printf '\nタイムアウト(%ds)。揃った分だけでマージするには review-merge を手動実行してください。\n' "$timeout" >&2
            return 2
        fi
        sleep "$interval"
    done
}

main "$@"
