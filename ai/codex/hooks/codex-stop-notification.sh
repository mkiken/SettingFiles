#!/bin/bash
export LANG="${LANG:-en_US.UTF-8}"

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

if [[ -z "${transcript_path}" || "${transcript_path}" == "null" ]]; then
    notify "$(build_notification_title "🤖" "Codex終了" "${EMOJI_ID_CODEX}")" 'transcript pathが見つかりません' "${NOTIFICATION_SOUND}"
    exit 0
fi

if [[ ! -f "${transcript_path}" ]]; then
    notify "$(build_notification_title "🤖" "Codex終了" "${EMOJI_ID_CODEX}")" 'セッションが終了しました' "${NOTIFICATION_SOUND}"
    exit 0
fi

debug_log "Processing transcript for summary generation..."

summary=""
user_messages=()
assistant_messages=()
total_messages=0

# Codex rollout JSONL: type=="response_item" + payload.type=="message" + payload.role=="user"|"assistant"
while IFS= read -r line; do
    if [[ -n "${line}" ]]; then
        line_type=$(echo "${line}" | jq -r '.type // empty')

        if [[ "${line_type}" != "response_item" ]]; then
            continue
        fi

        payload_type=$(echo "${line}" | jq -r '.payload.type // empty')
        if [[ "${payload_type}" != "message" ]]; then
            continue
        fi

        role=$(echo "${line}" | jq -r '.payload.role // empty')
        # developer ロールはシステムメッセージなのでスキップ
        if [[ "${role}" == "developer" ]]; then
            continue
        fi

        # content は input_text / output_text タイプの配列
        content=$(echo "${line}" | jq -r '.payload.content[] | select(.type == "input_text" or .type == "output_text") | .text' 2>/dev/null | tr '\n' ' ' | sed 's/  */ /g' | sed 's/^ *//;s/ *$//')

        debug_log "Found message: role=${role}, content_length=${#content}"

        is_system_message() {
            local msg="$1"

            # AGENTS.md auto-inject やenvironment_contextはCodexが自動挿入するsystem context
            if [[ "${msg}" =~ ^'# AGENTS.md instructions for' ]]; then
                return 0
            fi
            if [[ "${msg}" =~ ^'<environment_context>' ]]; then
                return 0
            fi
            if [[ "${msg}" =~ ^'<command-message>' ]]; then
                return 0
            fi

            # スラッシュコマンドは意図的な入力として扱う
            if [[ "${msg}" =~ ^/ ]]; then
                return 1
            fi

            # 既知のClaude Codeシステムタグパターン（Codexにも共通する可能性あり）
            if [[ "${msg}" =~ ^[[:space:]]*'<'(system-reminder|user-prompt-submit-hook|tool-result|antml) ]]; then
                return 0
            fi

            if [[ "${msg}" =~ ^Caveat: ]]; then
                return 0
            fi

            if [[ ${#msg} -lt 4 ]]; then
                return 0
            fi

            return 1
        }

        if [[ "${role}" == "user" && -n "${content}" && "${content}" != "null" ]]; then
            if ! is_system_message "${content}"; then
                user_messages+=("${content}")
                ((total_messages++))
                debug_log "Added user message: ${#content} chars"
            else
                debug_log "Skipping system message: ${content:0:100}..."
            fi
        elif [[ "${role}" == "assistant" && -n "${content}" && "${content}" != "null" ]]; then
            assistant_messages+=("${content}")
            ((total_messages++))
            debug_log "Added assistant message: ${#content} chars"
        fi
    fi
done < "${transcript_path}"

last_user_message=""
if [[ ${#user_messages[@]} -gt 0 ]]; then
    last_user_message="${user_messages[${#user_messages[@]}-1]}"
fi

debug_log "Total user messages: ${#user_messages[@]}, assistant messages: ${#assistant_messages[@]}"

# セッション時間計算
session_duration=""
session_duration_formatted=""
completion_time=""
if [[ -f "${transcript_path}" ]]; then
    filtered_log=$(grep -v '"type":"session_meta"' "${transcript_path}")

    first_timestamp=$(echo "${filtered_log}" | jq -r 'select(.timestamp) | .timestamp' 2>/dev/null | grep -v '^null$' | head -1)
    last_timestamp=$(echo "${filtered_log}" | jq -r 'select(.timestamp) | .timestamp' 2>/dev/null | grep -v '^null$' | tail -1)

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
user_count=0
if [[ -n "${user_messages[*]:-}" ]]; then
    user_count=${#user_messages[@]}
fi

if [[ ${user_count} -gt 0 ]]; then
    if [[ -n "${session_duration_formatted}" ]]; then
        stats_line="🔄${user_count} ⏳${session_duration_formatted}"
    else
        stats_line="🔄${user_count}"
    fi

    last_user_message=$(echo "${last_user_message}" | tr '\n' ' ' | sed 's/  */ /g' | sed 's/^ *//;s/ *$//')
    debug_log "Final last_user_message: ${last_user_message:0:100}"

    msg_line="${task_type} ${last_user_message}"

    max_msg_length=80
    if [[ ${#msg_line} -gt ${max_msg_length} ]]; then
        prefix_length=$(( ${#task_type} + 1 ))
        ellipsis_length=3
        max_message_length=$((max_msg_length - prefix_length - ellipsis_length))

        truncated_message="${last_user_message:0:${max_message_length}}"
        msg_line="${task_type} ${truncated_message}..."

        if [[ ${#msg_line} -gt ${max_msg_length} ]]; then
            max_message_length=$((max_message_length - 5))
            truncated_message="${last_user_message:0:${max_message_length}}"
            msg_line="${task_type} ${truncated_message}..."
        fi
    fi

    summary="${msg_line}"$'\n'"${stats_line}"
else
    summary="💭 セッションが開始されましたが、メッセージはありませんでした"
fi

notification_title=$(build_notification_title "✅" "Codex終了" "${EMOJI_ID_CODEX}")

debug_log "Sending notification: title='${notification_title}', message='${summary}'"
notify "${notification_title}" "${summary}" "${NOTIFICATION_SOUND}" "${notification_group}" "${completion_time}"

debug_log "=== Codex Notification Hook Completed ==="
