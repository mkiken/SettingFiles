#!/bin/bash
# 通知タイトル組立・時間フォーマットの共通ヘルパー
# 時刻・tmuxウィンドウ番号の付与は notify 関数が担う。
# Usage: build_notification_title "⚠️" "入力待ち"
#        build_notification_title "⚠️" "Claude承認待ち" "✴️"  # AI識別子プレフィックス付き

# 秒数を人間が読みやすい形式に変換する
# Usage: format_duration 3661 → "1h1m"
format_duration() {
    local total_seconds=$1
    local hours=$((total_seconds / 3600))
    local minutes=$(((total_seconds % 3600) / 60))
    local seconds=$((total_seconds % 60))

    if [[ ${hours} -gt 0 ]]; then
        echo "${hours}h${minutes}m"
    elif [[ ${minutes} -gt 0 ]]; then
        echo "${minutes}m${seconds}s"
    else
        echo "${seconds}s"
    fi
}

# 通知タイトル本文を組み立てる
# 引数:
#   $1: status_emoji - ステータス絵文字 (例: "⚠️")
#   $2: label_text   - タイトル本文 (例: "入力待ち")
#   $3: id_prefix    - AI識別子プレフィックス (省略可。例: "✴️" for Claude, "💎" for Gemini)
# 出力例: "✴️⚠️ Claude承認待ち"
build_notification_title() {
    local status_emoji="$1"
    local label_text="$2"
    local id_prefix="${3:-}"
    echo "${id_prefix}${status_emoji} ${label_text}"
}
