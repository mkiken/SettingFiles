#!/bin/bash
# 通知タイトルの統一フォーマット生成ヘルパー
# Usage: build_notification_title "⚠️" "入力待ち"
#        build_notification_title "⚠️" "Claude承認待ち" "✴️"  # AI識別子プレフィックス付き

_TMUX_NOTIFICATION_TITLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
source "${_TMUX_NOTIFICATION_TITLE_DIR}/tmux_window_info.sh"

# 通知タイトルをtmuxウィンドウ番号と現在時刻付きで生成する
# 引数:
#   $1: status_emoji  - ステータス絵文字 (例: "⚠️")
#   $2: label_text    - タイトル本文 (例: "入力待ち")
#   $3: id_prefix     - AI識別子プレフィックス (省略可。例: "✴️" for Claude, "💎" for Gemini)
# 出力例: "⚠️ 入力待ち 🖥️3 🕰️14:30:25"
build_notification_title() {
    local status_emoji="$1"
    local label_text="$2"
    local id_prefix="${3:-}"
    local tmux_label
    tmux_label=$(get_tmux_window_label)
    local current_time
    current_time=$(date "+%H:%M:%S")
    echo "${id_prefix}${status_emoji} ${label_text}${tmux_label} 🕰️${current_time}"
}
