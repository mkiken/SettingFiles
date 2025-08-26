#!/bin/bash

# Claude Code Status Line Script

# 実行権限を設定
chmod +x "$0" 2>/dev/null || true

# 標準入力からJSONデータを取得
input=$(cat)

# 基本情報を取得
current_dir=$(echo "$input" | jq -r '.workspace.current_dir')
model_name=$(echo "$input" | jq -r '.model.display_name')
model_id=$(echo "$input" | jq -r '.model.id' | sed 's/^claude-//')
version=$(echo "$input" | jq -r '.version // ""')
exceeds_200k=$(echo "$input" | jq -r '.exceeds_200k_tokens // false')

# Git情報を取得
git_info=""
if [ -d "$current_dir/.git" ]; then
    cd "$current_dir" || exit || exit
    branch=$(git symbolic-ref --short HEAD 2>/dev/null || git describe --tags --exact-match 2>/dev/null || git rev-parse --short HEAD 2>/dev/null)
    status=$(git status --porcelain 2>/dev/null)
    if [ -n "$status" ]; then
        git_status=" *"
    else
        git_status=""
    fi
    git_info=" (${branch}${git_status})"
fi

# 拡張情報を取得（costオブジェクト内から取得）
cost=$(echo "$input" | jq -r '.cost.total_cost_usd // 0')
duration_ms=$(echo "$input" | jq -r '.cost.total_duration_ms // 0')
lines_added=$(echo "$input" | jq -r '.cost.total_lines_added // 0')
lines_deleted=$(echo "$input" | jq -r '.cost.total_lines_removed // 0')

# 拡張情報の文字列を構築（利用可能な場合のみ）
extended_info=""
extended_info_parts=()

# コスト（USD表示、小数点2桁まで、常に表示）
cost_formatted=$(printf "%.2f" "${cost:-0}")
extended_info_parts+=("\$$cost_formatted")

# 実行時間（ミリ秒を秒に変換）
if [ "$duration_ms" != "0" ] && [ -n "$duration_ms" ]; then
    duration_sec=$(echo "scale=1; $duration_ms / 1000" | bc)
    extended_info_parts+=("${duration_sec}s")
fi

# 追加/削除行数（常に表示）
extended_info_parts+=("+${lines_added:-0}")
extended_info_parts+=("-${lines_deleted:-0}")

# 配列が空でない場合のみ拡張情報を構築
if [ ${#extended_info_parts[@]} -gt 0 ]; then
    IFS="|"
    extended_info=" (${extended_info_parts[*]})"
    unset IFS
fi

# 200k警告アイコン
warning=""
if [ "$exceeds_200k" = "true" ]; then
    warning=" ⚠️"
fi

# ステータスラインを出力
printf "\033[34m%s\033[0m%s \033[35m[%s(%s)]\033[0m\033[33m%s\033[0m%s \033[90mv%s\033[0m" \
    "$(basename "$current_dir")" \
    "$git_info" \
    "$model_name" \
    "$model_id" \
    "$extended_info" \
    "$warning" \
    "$version"