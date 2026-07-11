#!/bin/bash
export LANG="${LANG:-en_US.UTF-8}"

HOOK_ERROR_LOG="${TMPDIR:-/tmp}/codex-stop-notification-error.log"
exec >/dev/null
exec 2>>"${HOOK_ERROR_LOG}"

NOTIFICATION_SOUND='Glass'

DEBUG_ENABLED=false
DEBUG_LOG="/tmp/codex-hook-debug.log"

# プラットフォーム識別（共通ヘッダの build_ai_title / hook_fallback_notify 等が参照）
AI_HOOK_LABEL='Codex'

# 共通ヘッダ: notify/絵文字定義/タイトル生成/tmuxアイコン操作の読み込みと debug_log 定義
source "${SET:-$HOME/Desktop/repository/SettingFiles/}shell/tmux/ai_notification_hook_common.sh"

# エラーハンドリング方針: set -e は使わない（共通ヘッダのコメント参照）

HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
CODEX_HOOK_COMMON="${HOOK_DIR}/codex_hook_common.py"
if [[ ! -f "${CODEX_HOOK_COMMON}" ]]; then
    CODEX_HOOK_COMMON="${SET:-$HOME/Desktop/repository/SettingFiles/}ai/codex/hooks/codex_hook_common.py"
fi

debug_log "=== Codex Notification Hook Started ==="

hook_input=$(cat)
debug_log "Hook input received: ${hook_input}"

if ! command -v jq &> /dev/null; then
    hook_fallback_notify 'jqが見つかりません'
    exit 1
fi

hook_event_name=$(echo "${hook_input}" | jq -r '.hook_event_name')
transcript_path=$(echo "${hook_input}" | jq -r '.transcript_path')
debug_log "Hook event: ${hook_event_name}"
debug_log "Transcript path: ${transcript_path}"

session_id=$(derive_session_id "${hook_input}" "${transcript_path}")
notification_group=$(build_notification_group "${session_id}")
debug_log "Session ID: ${session_id}"

# Mac通知とtmuxアイコンの両方をこのフックが所有する（pyフックは進行中🤖のみ担当）。
# アイコンは notify --tmux-icon に統合せず、イベント確定直後に先行設定する。
# notify は要約生成の後になり、統合するとアイコン表示が遅れるため。
if [[ "${hook_event_name}" == "PermissionRequest" ]]; then
    update_tmux_window_name "${EMOJI_STATUS_NOTIFICATION}" "${AI_HOOK_EMOJI_ID}"

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

    notification_body=$(truncate_line "$(normalize_oneline "${notification_body}")" 140)

    debug_log "Sending permission request notification: ${notification_body}"
    notify "$(build_ai_title "⚠️" "承認待ち")" "${notification_body}" "Hero" "${notification_group}" || true
    exit 0
fi

if [[ ! -f "${CODEX_HOOK_COMMON}" ]]; then
    hook_fallback_notify 'hook共通モジュールが見つかりません'
    exit 0
fi

debug_log "Processing hook input with common analyzer..."
analysis_json=$(printf '%s' "${hook_input}" | python3 "${CODEX_HOOK_COMMON}" analyze 2>>"${HOOK_ERROR_LOG}")
analysis_status=$?
if [[ ${analysis_status} -ne 0 || -z "${analysis_json}" ]]; then
    hook_fallback_notify 'hook解析に失敗しました'
    exit 0
fi
if ! echo "${analysis_json}" | jq -e . >/dev/null 2>&1; then
    hook_fallback_notify 'hook解析結果が不正です'
    exit 0
fi

is_subagent=$(echo "${analysis_json}" | jq -r '.is_subagent_session // false')
if [[ "${hook_event_name}" == "Stop" && "${is_subagent}" == "true" ]]; then
    debug_log "Skipping completion notification for subagent session: ${session_id}"
    exit 0
fi

waiting_for_user_response=$(echo "${analysis_json}" | jq -r '.waiting_for_user_response // false')

# tmuxアイコン先行設定（応答待ちなら✋、完了なら✅）。notify に統合しない理由は PermissionRequest 側のコメント参照。
if [[ "${waiting_for_user_response}" == "true" ]]; then
    update_tmux_window_name "${EMOJI_STATUS_NOTIFICATION}" "${AI_HOOK_EMOJI_ID}"
else
    update_tmux_window_name "${EMOJI_STATUS_COMPLETED}" "${AI_HOOK_EMOJI_ID}"
fi

summary=""
last_user_message=$(echo "${analysis_json}" | jq -r '.last_user_message // ""')
last_assistant_message=$(echo "${analysis_json}" | jq -r '.last_assistant_message // ""')
user_count=$(echo "${analysis_json}" | jq -r '.user_message_count // 0')
assistant_count=$(echo "${analysis_json}" | jq -r '.assistant_message_count // 0')
first_timestamp=$(echo "${analysis_json}" | jq -r '.first_timestamp // ""')
last_timestamp=$(echo "${analysis_json}" | jq -r '.last_timestamp // ""')

debug_log "Total user messages: ${user_count}, assistant messages: ${assistant_count}"
debug_log "Waiting for user response: ${waiting_for_user_response}"

# セッション時間計算
debug_log "First timestamp: ${first_timestamp}"
debug_log "Last timestamp: ${last_timestamp}"

session_duration_formatted=$(format_session_duration "${first_timestamp}" "${last_timestamp}")
completion_time=$(format_completion_time_jst "${last_timestamp}")
debug_log "Session duration: ${session_duration_formatted}, completion time (JST): ${completion_time}"

# タスク種別推測
task_type=$(guess_task_type_emoji "${last_user_message}")

# 要約を作成（メッセージなしのセッションでは空になる）
summary_message="${last_user_message}"
summary_task_type="${task_type}"
if [[ "${waiting_for_user_response}" == "true" ]]; then
    summary_message="${last_assistant_message}"
    summary_task_type="✋"
fi
debug_log "Final summary_message: ${summary_message:0:100}"
summary=$(build_session_summary "${summary_task_type}" "${summary_message}" "${user_count}" "${session_duration_formatted}")

notification_sound="${NOTIFICATION_SOUND}"
if [[ "${waiting_for_user_response}" == "true" ]]; then
    notification_title=$(build_ai_title "✋" "応答待ち")
    notification_sound="Hero"
else
    notification_title=$(build_ai_title "✅" "終了")
fi

debug_log "Sending notification: title='${notification_title}', message='${summary}'"
notify "${notification_title}" "${summary:-💭 セッションが開始されましたが、メッセージはありませんでした}" "${notification_sound}" "${notification_group}" "${completion_time}"

debug_log "=== Codex Notification Hook Completed ==="
