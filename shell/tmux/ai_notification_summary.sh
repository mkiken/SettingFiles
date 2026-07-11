#!/bin/bash
# 通知shフック共通の要約ヘルパー（claude/gemini/codex）
# 依存: format_duration (shell/tmux/tmux_notification_title.sh)

# ISO 8601タイムスタンプをエポック秒へ変換（macOS BSD date）。失敗時は空出力。
# Usage: iso8601_to_epoch "2026-06-27T00:01:00.000Z"
iso8601_to_epoch() {
    date -j -f "%Y-%m-%dT%H:%M:%S" "${1%.*}" "+%s" 2>/dev/null
}

# セッション時間を人間可読形式で出力（例: "1h1m"）。計算不能時は空出力。
# Usage: format_session_duration <first_iso> <last_iso>
format_session_duration() {
    local first="$1" last="$2" start_epoch end_epoch
    [[ -z "${first}" || "${first}" == "null" || -z "${last}" || "${last}" == "null" ]] && return 0
    start_epoch=$(iso8601_to_epoch "${first}")
    end_epoch=$(iso8601_to_epoch "${last}")
    [[ -z "${start_epoch}" || -z "${end_epoch}" ]] && return 0
    format_duration $((end_epoch - start_epoch))
}

# 完了時刻をJST HH:MM:SSで出力（UTC+9時間）。計算不能時は空出力。
# Usage: format_completion_time_jst <last_iso>
format_completion_time_jst() {
    local last="$1" end_epoch
    [[ -z "${last}" || "${last}" == "null" ]] && return 0
    end_epoch=$(iso8601_to_epoch "${last}")
    [[ -z "${end_epoch}" ]] && return 0
    date -r $((end_epoch + 32400)) "+%H:%M:%S" 2>/dev/null
}

# 最終ユーザーメッセージからタスク種別絵文字を推測して出力（デフォルト 💬）
# Usage: guess_task_type_emoji <message>
guess_task_type_emoji() {
    local msg="$1"
    if [[ "${msg}" =~ (実装|コード|プログラム|関数|バグ|修正|追加|作成) ]]; then echo "💻" # コーディング
    elif [[ "${msg}" =~ (検索|調べ|探し|find|grep|確認) ]]; then echo "🔍" # 検索・調査
    elif [[ "${msg}" =~ (説明|教え|解説|どう|なぜ|what|how) ]]; then echo "📚" # 説明・学習
    elif [[ "${msg}" =~ (テスト|test|チェック|確認) ]]; then echo "🧪" # テスト・検証
    else echo "💬" # 一般的な質問
    fi
}
