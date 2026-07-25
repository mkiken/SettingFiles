#!/bin/bash
# AIレビューのランディレクトリ管理。
# 使い方:
#   ai_review_run_dir.sh <pr_number>            新規ランディレクトリを作成しパスを出力
#   ai_review_run_dir.sh --latest <pr_number>   最新ランディレクトリの実体パスを出力(作成しない)
# 環境変数:
#   AI_REVIEW_CACHE_ROOT  ベースディレクトリ(default: ~/.cache/ai-review)
#   AI_REVIEW_RUN_ID      run-idの固定(テスト用。default: date +%Y%m%d-%H%M%S)
#   AI_REVIEW_KEEP_RUNS   PRごとの保持ラン数(default: 5)

set -u

ai_review_repo_slug() {
    local url
    url=$(git remote get-url origin 2>/dev/null) || {
        echo "git remote origin が見つかりません" >&2
        return 1
    }
    local trimmed="${url%.git}"
    trimmed="${trimmed#ssh://}"
    trimmed="${trimmed#git@}"
    trimmed="${trimmed#https://}"
    trimmed="${trimmed#http://}"
    # scp形式 host:owner/repo をパス形式に揃える
    trimmed="${trimmed/:/\/}"
    local repo="${trimmed##*/}"
    local rest="${trimmed%/*}"
    local owner="${rest##*/}"
    if [[ -z "$owner" || -z "$repo" || "$owner" == "$trimmed" ]]; then
        echo "originのURLからowner/repoを解決できません: $url" >&2
        return 1
    fi
    printf '%s__%s\n' "$owner" "$repo"
}

ai_review_pr_dir() {
    local pr_number="$1"
    local slug
    slug=$(ai_review_repo_slug) || return 1
    printf '%s/%s/pr-%s\n' \
        "${AI_REVIEW_CACHE_ROOT:-$HOME/.cache/ai-review}" "$slug" "$pr_number"
}

ai_review_latest_run_dir() {
    local pr_dir
    pr_dir=$(ai_review_pr_dir "$1") || return 1
    local latest="${pr_dir}/latest"
    if [[ ! -d "$latest" ]]; then
        echo "最新ランが見つかりません: $latest" >&2
        return 1
    fi
    (cd "$latest" && pwd -P)
}

ai_review_prune_old_runs() {
    local pr_dir="$1"
    local keep="${AI_REVIEW_KEEP_RUNS:-5}"
    local -a runs=()
    local line
    # run-id形式(数字-数字)のディレクトリのみ対象。latestリンクは-type dに一致しない
    while IFS= read -r line; do
        runs+=("$line")
    done < <(find "$pr_dir" -mindepth 1 -maxdepth 1 -type d -name '[0-9]*-[0-9]*' | sort)
    local excess=$(( ${#runs[@]} - keep ))
    local i
    for (( i = 0; i < excess; i++ )); do
        trash "${runs[i]}"
    done
}

ai_review_create_run_dir() {
    local pr_number="$1"
    local pr_dir run_id run_dir
    pr_dir=$(ai_review_pr_dir "$pr_number") || return 1
    run_id="${AI_REVIEW_RUN_ID:-$(date +%Y%m%d-%H%M%S)}"
    run_dir="${pr_dir}/${run_id}"
    mkdir -p "$run_dir"
    ln -sfn "$run_id" "${pr_dir}/latest"
    ai_review_prune_old_runs "$pr_dir"
    printf '%s\n' "$run_dir"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    if [[ "${1:-}" == "--latest" ]]; then
        shift
        ai_review_latest_run_dir "${1:?PR番号が必要です}"
    else
        ai_review_create_run_dir "${1:?PR番号が必要です}"
    fi
fi
