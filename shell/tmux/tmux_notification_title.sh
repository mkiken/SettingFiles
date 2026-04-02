#!/bin/bash
# 通知タイトル生成・時間フォーマットの共通ヘルパー
# Usage: build_notification_title "⚠️" "入力待ち"
#        build_notification_title "⚠️" "Claude承認待ち" "✴️"           # AI識別子プレフィックス付き
#        build_notification_title "✅" "Claude終了" "✴️" "14:30:25"    # 時刻オーバーライド

_TMUX_NOTIFICATION_TITLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
source "${_TMUX_NOTIFICATION_TITLE_DIR}/tmux_window_info.sh"

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

# 通知タイトルをtmuxウィンドウ番号と現在時刻付きで生成する
# 引数:
#   $1: status_emoji   - ステータス絵文字 (例: "⚠️")
#   $2: label_text     - タイトル本文 (例: "入力待ち")
#   $3: id_prefix      - AI識別子プレフィックス (省略可。例: "✴️" for Claude, "💎" for Gemini)
#   $4: override_time  - 時刻文字列の上書き (省略可。例: "14:30:25"。省略時は現在時刻)
# 出力例: "⚠️ 入力待ち 🖥️3 🕰️14:30:25"
build_notification_title() {
    local status_emoji="$1"
    local label_text="$2"
    local id_prefix="${3:-}"
    local override_time="${4:-}"
    local tmux_label
    tmux_label=$(get_tmux_window_label)
    local display_time="${override_time:-$(date "+%H:%M:%S")}"
    echo "${id_prefix}${status_emoji} ${label_text}${tmux_label} 🕰️${display_time}"
}
