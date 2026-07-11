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

# hook入力の必要フィールドを1回のjqでまとめて抽出（フィールドごとのjq起動を削減）。
# 抽出失敗時はevalが空になり、直後のデフォルト代入で既存のフォールバック分岐へ劣化する。
eval "$(printf '%s' "${hook_input}" | jq -r '
    @sh "hook_event_name=\(.hook_event_name // "")",
    @sh "transcript_path=\(.transcript_path // "")",
    @sh "session_id=\(.session_id // "")",
    @sh "tool_name=\(.tool_name // "tool")",
    @sh "approval_reason=\(.tool_input.description // "")",
    @sh "tool_command=\(.tool_input.command // "")"
' 2>/dev/null)"
hook_event_name="${hook_event_name:-}"
transcript_path="${transcript_path:-}"
session_id="${session_id:-}"
tool_name="${tool_name:-tool}"
approval_reason="${approval_reason:-}"
tool_command="${tool_command:-}"
debug_log "Hook event: ${hook_event_name}"
debug_log "Transcript path: ${transcript_path}"

# セッションID（グループ通知用）: hook入力から抽出済みの値を優先し、
# 無い場合のみ共通ヘルパーでtranscript_pathから導出する
if [[ -z "${session_id}" ]]; then
    session_id=$(derive_session_id '{}' "${transcript_path}")
fi
notification_group=$(build_notification_group "${session_id}")
debug_log "Session ID: ${session_id}"

# Mac通知とtmuxアイコンの両方をこのフックが所有する（pyフックは進行中🤖のみ担当）。
# アイコンは notify --tmux-icon に統合せず、イベント確定直後に先行設定する。
# notify は要約生成の後になり、統合するとアイコン表示が遅れるため。
if [[ "${hook_event_name}" == "PermissionRequest" ]]; then
    update_tmux_window_name "${EMOJI_STATUS_NOTIFICATION}" "${AI_HOOK_EMOJI_ID}"

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
# 解析結果はshlex引用済みの VAR=値 行（claude_transcript_analyze.py と同じ契約）。
# eval 1回で取り込めるため、旧実装のjq検証＋フィールドごとのjq抽出は不要。
analysis=$(printf '%s' "${hook_input}" | python3 "${CODEX_HOOK_COMMON}" analyze 2>>"${HOOK_ERROR_LOG}")
analysis_status=$?
if [[ ${analysis_status} -ne 0 || -z "${analysis}" ]]; then
    hook_fallback_notify 'hook解析に失敗しました'
    exit 0
fi
eval "${analysis}"
IS_SUBAGENT_SESSION="${IS_SUBAGENT_SESSION:-false}"
WAITING_FOR_USER_RESPONSE="${WAITING_FOR_USER_RESPONSE:-false}"
LAST_USER_MESSAGE="${LAST_USER_MESSAGE:-}"
LAST_ASSISTANT_MESSAGE="${LAST_ASSISTANT_MESSAGE:-}"
USER_MESSAGE_COUNT="${USER_MESSAGE_COUNT:-0}"
ASSISTANT_MESSAGE_COUNT="${ASSISTANT_MESSAGE_COUNT:-0}"
FIRST_TIMESTAMP="${FIRST_TIMESTAMP:-}"
LAST_TIMESTAMP="${LAST_TIMESTAMP:-}"

if [[ "${hook_event_name}" == "Stop" && "${IS_SUBAGENT_SESSION}" == "true" ]]; then
    debug_log "Skipping completion notification for subagent session: ${session_id}"
    exit 0
fi

# tmuxアイコン先行設定（応答待ちなら✋、完了なら✅）。notify に統合しない理由は PermissionRequest 側のコメント参照。
if [[ "${WAITING_FOR_USER_RESPONSE}" == "true" ]]; then
    update_tmux_window_name "${EMOJI_STATUS_NOTIFICATION}" "${AI_HOOK_EMOJI_ID}"
else
    update_tmux_window_name "${EMOJI_STATUS_COMPLETED}" "${AI_HOOK_EMOJI_ID}"
fi

debug_log "Total user messages: ${USER_MESSAGE_COUNT}, assistant messages: ${ASSISTANT_MESSAGE_COUNT}"
debug_log "Waiting for user response: ${WAITING_FOR_USER_RESPONSE}"

# セッション時間計算
debug_log "First timestamp: ${FIRST_TIMESTAMP}"
debug_log "Last timestamp: ${LAST_TIMESTAMP}"

session_duration_formatted=$(format_session_duration "${FIRST_TIMESTAMP}" "${LAST_TIMESTAMP}")
completion_time=$(format_completion_time_jst "${LAST_TIMESTAMP}")
debug_log "Session duration: ${session_duration_formatted}, completion time (JST): ${completion_time}"

# タスク種別推測
task_type=$(guess_task_type_emoji "${LAST_USER_MESSAGE}")

# 要約を作成（メッセージなしのセッションでは空になる）
summary_message="${LAST_USER_MESSAGE}"
summary_task_type="${task_type}"
if [[ "${WAITING_FOR_USER_RESPONSE}" == "true" ]]; then
    summary_message="${LAST_ASSISTANT_MESSAGE}"
    summary_task_type="✋"
fi
debug_log "Final summary_message: ${summary_message:0:100}"
summary=$(build_session_summary "${summary_task_type}" "${summary_message}" "${USER_MESSAGE_COUNT}" "${session_duration_formatted}")

notification_sound="${NOTIFICATION_SOUND}"
if [[ "${WAITING_FOR_USER_RESPONSE}" == "true" ]]; then
    notification_title=$(build_ai_title "✋" "応答待ち")
    notification_sound="Hero"
else
    notification_title=$(build_ai_title "✅" "終了")
fi

debug_log "Sending notification: title='${notification_title}', message='${summary}'"
notify "${notification_title}" "${summary:-💭 セッションが開始されましたが、メッセージはありませんでした}" "${notification_sound}" "${notification_group}" "${completion_time}"

debug_log "=== Codex Notification Hook Completed ==="
