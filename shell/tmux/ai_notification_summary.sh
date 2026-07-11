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

# 統計行を出力（例: "🔄3 ⏳5m2s"、時間なしは "🔄3"）
# Usage: build_stats_line <user_count> <duration_formatted>
build_stats_line() {
    local user_count="$1" duration="$2"
    if [[ -n "${duration}" ]]; then echo "🔄${user_count} ⏳${duration}"; else echo "🔄${user_count}"; fi
}

# メッセージ行を組み立て（改行除去・空白正規化・最大長超は短縮して"..."付与）
# Usage: build_summary_msg_line <task_emoji> <message> [max_len=80]
build_summary_msg_line() {
    local emoji="$1" message="$2" max_len="${3:-80}"
    local msg_line prefix_length max_message_length
    message=$(echo "${message}" | tr '\n' ' ' | sed 's/  */ /g' | sed 's/^ *//;s/ *$//')
    msg_line="${emoji} ${message}"
    if [[ ${#msg_line} -gt ${max_len} ]]; then
        prefix_length=$(( ${#emoji} + 1 ))
        max_message_length=$((max_len - prefix_length - 3))
        msg_line="${emoji} ${message:0:${max_message_length}}..."
        # 全角絵文字などで幅計算がずれた場合の再短縮
        if [[ ${#msg_line} -gt ${max_len} ]]; then
            max_message_length=$((max_message_length - 5))
            msg_line="${emoji} ${message:0:${max_message_length}}..."
        fi
    fi
    echo "${msg_line}"
}

# hook入力JSONのsession_id、無ければtranscriptファイル名から導出（claude/codex共通形）
# Usage: derive_session_id <hook_input_json> <transcript_path>
derive_session_id() {
    local sid
    sid=$(echo "$1" | jq -r '.session_id // empty')
    [[ -z "${sid}" ]] && sid=$(basename "$2" .jsonl)
    echo "${sid}"
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
