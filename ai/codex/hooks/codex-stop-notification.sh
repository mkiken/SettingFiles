#!/bin/bash
export LANG="${LANG:-en_US.UTF-8}"

HOOK_ERROR_LOG="${TMPDIR:-/tmp}/codex-stop-notification-error.log"
exec >/dev/null
exec 2>>"${HOOK_ERROR_LOG}"

source "${SET:-$HOME/Desktop/repository/SettingFiles/}shell/zsh/alias/notification.zsh"
source "${SET:-$HOME/Desktop/repository/SettingFiles/}shell/tmux/tmux_emoji.conf"
source "${SET:-$HOME/Desktop/repository/SettingFiles/}shell/tmux/tmux_window_info.sh"
source "${SET:-$HOME/Desktop/repository/SettingFiles/}shell/tmux/tmux_notification_title.sh"

NOTIFICATION_SOUND='Glass'

DEBUG_ENABLED=false
DEBUG_LOG="/tmp/codex-hook-debug.log"

if [[ "${DEBUG_ENABLED}" == "true" ]]; then
    set -e
fi

debug_log() {
    if [[ "${DEBUG_ENABLED}" == "true" ]]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "${DEBUG_LOG}"
    fi
}

HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
CODEX_HOOK_COMMON="${HOOK_DIR}/codex_hook_common.py"
if [[ ! -f "${CODEX_HOOK_COMMON}" ]]; then
    CODEX_HOOK_COMMON="${SET:-$HOME/Desktop/repository/SettingFiles/}ai/codex/hooks/codex_hook_common.py"
fi

debug_log "=== Codex Notification Hook Started ==="

hook_input=$(cat)
debug_log "Hook input received: ${hook_input}"

if ! command -v jq &> /dev/null; then
    notify "$(build_notification_title "🤖" "Codex終了" "${EMOJI_ID_CODEX}")" 'jqが見つかりません' "${NOTIFICATION_SOUND}"
    exit 1
fi

hook_event_name=$(echo "${hook_input}" | jq -r '.hook_event_name')
transcript_path=$(echo "${hook_input}" | jq -r '.transcript_path')
debug_log "Hook event: ${hook_event_name}"
debug_log "Transcript path: ${transcript_path}"

session_id=$(echo "${hook_input}" | jq -r '.session_id // empty')
if [[ -z "${session_id}" ]]; then
    session_id=$(basename "${transcript_path}" .jsonl)
fi
notification_group="codex-${session_id}"
debug_log "Session ID: ${session_id}"

if [[ "${hook_event_name}" == "PermissionRequest" ]]; then
    tool_name=$(echo "${hook_input}" | jq -r '.tool_name // "tool"')
    approval_reason=$(echo "${hook_input}" | jq -r '.tool_input.description // empty')
    tool_command=$(echo "${hook_input}" | jq -r '.tool_input.command // empty')

    if [[ -n "${approval_reason}" ]]; then
        notification_body="${approval_reason}"
    elif [[ -n "${tool_command}" ]]; then
        notification_body="${tool_name}: ${tool_command}"
    else
        notification_body="${tool_name} の承認が必要です"
    fi

    notification_body=$(echo "${notification_body}" | tr '\n' ' ' | sed 's/  */ /g' | sed 's/^ *//;s/ *$//')
    max_permission_length=140
    if [[ ${#notification_body} -gt ${max_permission_length} ]]; then
        notification_body="${notification_body:0:${max_permission_length}}..."
    fi

    debug_log "Sending permission request notification: ${notification_body}"
    notify "$(build_notification_title "⚠️" "Codex承認待ち" "${EMOJI_ID_CODEX}")" "${notification_body}" "Hero" "${notification_group}" || true
    exit 0
fi

if [[ ! -f "${CODEX_HOOK_COMMON}" ]]; then
    notify "$(build_notification_title "🤖" "Codex終了" "${EMOJI_ID_CODEX}")" 'hook共通モジュールが見つかりません' "${NOTIFICATION_SOUND}"
    exit 0
fi

debug_log "Processing hook input with common analyzer..."
analysis_json=$(printf '%s' "${hook_input}" | python3 "${CODEX_HOOK_COMMON}" analyze 2>>"${HOOK_ERROR_LOG}")
analysis_status=$?
if [[ ${analysis_status} -ne 0 || -z "${analysis_json}" ]]; then
    notify "$(build_notification_title "🤖" "Codex終了" "${EMOJI_ID_CODEX}")" 'hook解析に失敗しました' "${NOTIFICATION_SOUND}"
    exit 0
fi
if ! echo "${analysis_json}" | jq -e . >/dev/null 2>&1; then
    notify "$(build_notification_title "🤖" "Codex終了" "${EMOJI_ID_CODEX}")" 'hook解析結果が不正です' "${NOTIFICATION_SOUND}"
    exit 0
fi

is_subagent=$(echo "${analysis_json}" | jq -r '.is_subagent_session // false')
if [[ "${hook_event_name}" == "Stop" && "${is_subagent}" == "true" ]]; then
    debug_log "Skipping completion notification for subagent session: ${session_id}"
    exit 0
fi

if [[ -z "${transcript_path}" || "${transcript_path}" == "null" ]]; then
    notify "$(build_notification_title "🤖" "Codex終了" "${EMOJI_ID_CODEX}")" 'transcript pathが見つかりません' "${NOTIFICATION_SOUND}"
    exit 0
fi

if [[ ! -f "${transcript_path}" ]]; then
    notify "$(build_notification_title "🤖" "Codex終了" "${EMOJI_ID_CODEX}")" 'セッションが終了しました' "${NOTIFICATION_SOUND}"
    exit 0
fi

summary=""
last_user_message=$(echo "${analysis_json}" | jq -r '.last_user_message // ""')
last_assistant_message=$(echo "${analysis_json}" | jq -r '.last_assistant_message // ""')
waiting_for_user_response=$(echo "${analysis_json}" | jq -r '.waiting_for_user_response // false')
user_count=$(echo "${analysis_json}" | jq -r '.user_message_count // 0')
assistant_count=$(echo "${analysis_json}" | jq -r '.assistant_message_count // 0')
first_timestamp=$(echo "${analysis_json}" | jq -r '.first_timestamp // ""')
last_timestamp=$(echo "${analysis_json}" | jq -r '.last_timestamp // ""')

debug_log "Total user messages: ${user_count}, assistant messages: ${assistant_count}"
debug_log "Waiting for user response: ${waiting_for_user_response}"

# セッション時間計算
session_duration=""
session_duration_formatted=""
completion_time=""
debug_log "First timestamp: ${first_timestamp}"
debug_log "Last timestamp: ${last_timestamp}"

if [[ -n "${first_timestamp}" && "${first_timestamp}" != "null" && -n "${last_timestamp}" && "${last_timestamp}" != "null" ]]; then
    start_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${first_timestamp%.*}" "+%s" 2>/dev/null)
    end_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${last_timestamp%.*}" "+%s" 2>/dev/null)

    if [[ -n "${start_epoch}" && -n "${end_epoch}" ]]; then
        session_duration=$((end_epoch - start_epoch))
        session_duration_formatted=$(format_duration ${session_duration})
        debug_log "Session duration: ${session_duration}s (${session_duration_formatted})"

        jst_epoch=$((end_epoch + 32400))
        completion_time=$(date -r "${jst_epoch}" "+%H:%M:%S" 2>/dev/null)
        debug_log "Completion time (JST): ${completion_time}"
    fi
fi

# タスク種別推測
task_type="💬"
if [[ "$last_user_message" =~ (実装|コード|プログラム|関数|バグ|修正|追加|作成) ]]; then
    task_type="💻"
elif [[ "$last_user_message" =~ (検索|調べ|探し|find|grep|確認) ]]; then
    task_type="🔍"
elif [[ "$last_user_message" =~ (説明|教え|解説|どう|なぜ|what|how) ]]; then
    task_type="📚"
elif [[ "$last_user_message" =~ (テスト|test|チェック|確認) ]]; then
    task_type="🧪"
fi

# 要約を作成
if [[ ${user_count} -gt 0 ]]; then
    if [[ -n "${session_duration_formatted}" ]]; then
        stats_line="🔄${user_count} ⏳${session_duration_formatted}"
    else
        stats_line="🔄${user_count}"
    fi

    summary_message="${last_user_message}"
    summary_task_type="${task_type}"
    if [[ "${waiting_for_user_response}" == "true" ]]; then
        summary_message="${last_assistant_message}"
        summary_task_type="✋"
    fi

    debug_log "Final summary_message: ${summary_message:0:100}"

    msg_line="${summary_task_type} ${summary_message}"

    max_msg_length=80
    if [[ ${#msg_line} -gt ${max_msg_length} ]]; then
        prefix_length=$(( ${#summary_task_type} + 1 ))
        ellipsis_length=3
        max_message_length=$((max_msg_length - prefix_length - ellipsis_length))

        truncated_message="${summary_message:0:${max_message_length}}"
        msg_line="${summary_task_type} ${truncated_message}..."

        if [[ ${#msg_line} -gt ${max_msg_length} ]]; then
            max_message_length=$((max_message_length - 5))
            truncated_message="${summary_message:0:${max_message_length}}"
            msg_line="${summary_task_type} ${truncated_message}..."
        fi
    fi

    summary="${msg_line}"$'\n'"${stats_line}"
else
    summary="💭 セッションが開始されましたが、メッセージはありませんでした"
fi

notification_sound="${NOTIFICATION_SOUND}"
if [[ "${waiting_for_user_response}" == "true" ]]; then
    notification_title=$(build_notification_title "✋" "Codex応答待ち" "${EMOJI_ID_CODEX}")
    notification_sound="Hero"
else
    notification_title=$(build_notification_title "✅" "Codex終了" "${EMOJI_ID_CODEX}")
fi

debug_log "Sending notification: title='${notification_title}', message='${summary}'"
notify "${notification_title}" "${summary}" "${notification_sound}" "${notification_group}" "${completion_time}"

debug_log "=== Codex Notification Hook Completed ==="
