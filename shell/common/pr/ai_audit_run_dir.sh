#!/bin/bash
# 設定監査のランディレクトリ管理。
# 使い方:
#   ai_audit_run_dir.sh <platform>            新規ランディレクトリを作成しパスを出力
#   ai_audit_run_dir.sh --latest <platform>   最新ランディレクトリの実体パスを出力(作成しない)
# 環境変数:
#   AI_AUDIT_CACHE_ROOT  ベースディレクトリ(default: ~/.cache/ai-audit)
#   AI_AUDIT_RUN_ID      run-idの固定(テスト用。default: date +%Y%m%d-%H%M%S)
#   AI_AUDIT_KEEP_RUNS   プラットフォームごとの保持ラン数(default: 5)
#
# レビュー側(ai_review_run_dir.sh)と違いgit originに依存しない。
# config-auditはリポジトリ外でも実行されるため、リポジトリ判定を挟まない。

set -u

ai_audit_platform_dir() {
    local platform="$1"
    case "$platform" in
        claude|codex|gemini) ;;
        *)
            echo "不正なプラットフォームです(claude/codex/geminiのいずれか): $platform" >&2
            return 1
            ;;
    esac
    printf '%s/%s\n' "${AI_AUDIT_CACHE_ROOT:-$HOME/.cache/ai-audit}" "$platform"
}

ai_audit_latest_run_dir() {
    local platform_dir
    platform_dir=$(ai_audit_platform_dir "$1") || return 1
    local latest="${platform_dir}/latest"
    if [[ ! -d "$latest" ]]; then
        echo "最新ランが見つかりません: $latest" >&2
        return 1
    fi
    (cd "$latest" && pwd -P)
}

ai_audit_prune_old_runs() {
    local platform_dir="$1"
    local keep="${AI_AUDIT_KEEP_RUNS:-5}"
    local -a runs=()
    local line
    # run-id形式(数字-数字)のディレクトリのみ対象。latestリンクは-type dに一致しない
    while IFS= read -r line; do
        runs+=("$line")
    done < <(find "$platform_dir" -mindepth 1 -maxdepth 1 -type d -name '[0-9]*-[0-9]*' | sort)
    local excess=$(( ${#runs[@]} - keep ))
    local i
    for (( i = 0; i < excess; i++ )); do
        trash "${runs[i]}"
    done
}

ai_audit_create_run_dir() {
    local platform="$1"
    local platform_dir run_id run_dir
    platform_dir=$(ai_audit_platform_dir "$platform") || return 1
    run_id="${AI_AUDIT_RUN_ID:-$(date +%Y%m%d-%H%M%S)}"
    run_dir="${platform_dir}/${run_id}"
    mkdir -p "$run_dir"
    ln -sfn "$run_id" "${platform_dir}/latest"
    ai_audit_prune_old_runs "$platform_dir"
    printf '%s\n' "$run_dir"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    if [[ "${1:-}" == "--latest" ]]; then
        shift
        ai_audit_latest_run_dir "${1:?プラットフォーム名が必要です}"
    else
        ai_audit_create_run_dir "${1:?プラットフォーム名が必要です}"
    fi
fi
