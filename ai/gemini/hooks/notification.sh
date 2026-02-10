#!/bin/bash

# notification関数を読み込み (SETが未定義の場合はHOMEから解決)
source "${SET:-$HOME/Desktop/repository/SettingFiles/}shell/zsh/alias/notification.zsh"

# デバッグフラグ (true/false)
DEBUG_ENABLED=true
DEBUG_LOG="/tmp/gemini-hook-debug.log"

# デバッグ関数
debug_log() {
    if [[ "${DEBUG_ENABLED}" == "true" ]]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "${DEBUG_LOG}"
    fi
}

debug_log "=== Gemini Notification Hook Started ==="

# hookからJSONを読み取り
hook_input=$(cat)
debug_log "Hook input received: ${hook_input}"

# jqが利用可能かチェック
if ! command -v jq &> /dev/null; then
    debug_log "Error: jq not found"
    exit 1
fi

# 通知タイトル
notification_title="🤖 Gemini CLI 応答完了"

# 通知メッセージ (簡易版)
# 将来的には hook_input から詳細を抽出して要約を表示できると良い
summary="Geminiからの応答を受信しました"

# 完了時刻
current_time=$(date "+%H:%M:%S")
notification_title="${notification_title} at 🕰️${current_time}"

debug_log "Sending notification: title='${notification_title}', message='${summary}'"

# notify関数を呼び出し
notify "${notification_title}" "${summary}" "Submarine"

debug_log "=== Gemini Notification Hook Completed ==="
