#!/bin/bash
export LANG="${LANG:-en_US.UTF-8}"

# 通知音設定 (変更する場合はここだけ編集)
NOTIFICATION_SOUND='Purr'

# デバッグフラグ (true/false)
DEBUG_ENABLED=false
DEBUG_LOG="/tmp/gemini-hook-debug.log"

# プラットフォーム識別（共通ヘッダの build_ai_title / hook_fallback_notify 等が参照）
AI_HOOK_LABEL='Gemini'

# 共通ヘッダ: notify/絵文字定義/タイトル生成/tmuxアイコン操作の読み込みと debug_log 定義
source "${SET:-$HOME/Desktop/repository/SettingFiles/}shell/tmux/ai_notification_hook_common.sh"

# エラーハンドリング方針: set -e は使わない（共通ヘッダのコメント参照）

debug_log "=== Gemini Notification Hook Started ==="

# Parse arguments
EVENT_TYPE="after_agent"
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --event) EVENT_TYPE="$2"; shift ;;
        *) ;;
    esac
    shift
done

debug_log "Event Type: ${EVENT_TYPE}"

# hookからJSONを読み取り
hook_input=$(cat)
debug_log "Hook input received: ${hook_input}"

# jqが利用可能かチェック
if ! command -v jq &> /dev/null; then
    debug_log "Error: jq not found"
    hook_fallback_notify 'jqが見つかりません'
    exit 1
fi

# hook入力の必要フィールドを1回のjqでまとめて抽出（フィールドごとのjq起動を削減）。
# ACTION_DETAILはnotificationイベント専用の派生値だが、hook_inputのみから決まるためここに同居させる
# （after_agentでは .details がnullなのでelse経由で空になるだけ）。
# try/catchは必須: 統合evalではACTION_DETAIL部の失敗が他フィールドまで巻き込むため、
# 失敗をフィールド単位の空文字列に隔離する。抽出全体の失敗時はevalが空になり、
# 直後のデフォルト代入で既存のフォールバック分岐へ劣化する。
eval "$(printf '%s' "${hook_input}" | jq -r '
    @sh "NOTIFICATION_TYPE=\(.notification_type // "")",
    @sh "transcript_path=\(.transcript_path // "")",
    @sh "session_id=\(.session_id // "")",
    @sh "ACTION_DETAIL=\(try (.details |
        if (.tool_name == "ask_user") then
            "❓ " + (.tool_input.questions | map(.question) | join(" / "))
        elif (.tool_name == "replace" or .tool_name == "write_file") then
            "📝 " + .tool_name + " (" + (.tool_input.file_path | split("/") | last) + ")"
        elif (.tool_name == "run_shell_command") then
            "💻 cmd (" + (.tool_input.command | split("\n")[0] | if length > 40 then .[0:40] + "..." else . end) + ")"
        elif (.type == "exec") then
            if (.rootCommand != null and .rootCommand != "") then ("Shell (" + .rootCommand + ")")
            elif (.command != null and .command != "") then ("Shell (" + (.command | split(" ")[0]) + ")")
            else "Shell" end
        elif (.type == "edit") then
            if (.fileName != null and .fileName != "") then ("Edit (" + .fileName + ")")
            else "Edit" end
        elif (.tool_name != null and .tool_name != "") then
             if (.rootCommand != null and .rootCommand != "") then (.tool_name + " (" + .rootCommand + ")")
             else .tool_name end
        elif (.rootCommand != null and .rootCommand != "") then .rootCommand
        elif (.title != null and .title != "") then .title
        else "" end
    ) catch "")"
' 2>/dev/null)"
NOTIFICATION_TYPE="${NOTIFICATION_TYPE:-}"
transcript_path="${transcript_path:-}"
session_id="${session_id:-}"
ACTION_DETAIL="${ACTION_DETAIL:-}"

# --- tmuxアイコン先行設定 ---
# Mac通知とtmuxアイコンの両方をこのフックが所有する（pyフックは進行中🤖とsession_endのみ担当）。
# アイコンは notify --tmux-icon に統合せず、イベント確定直後のここで設定する。
# notify は後続のトランスクリプト解析（要約生成）の後になり、統合するとアイコン表示が遅れるため。
if [[ "${EVENT_TYPE}" == "notification" ]]; then
    if [[ "${NOTIFICATION_TYPE}" != "ToolPermission" ]]; then
        debug_log "Ignoring notification type: ${NOTIFICATION_TYPE}"
        exit 0
    fi
    update_tmux_window_name "${EMOJI_STATUS_NOTIFICATION}" "${AI_HOOK_EMOJI_ID}"
elif [[ "${EVENT_TYPE}" == "after_agent" ]]; then
    update_tmux_window_name "${EMOJI_STATUS_COMPLETED}" "${AI_HOOK_EMOJI_ID}"
fi

# ------------------------------------------------------------------
# トランスクリプト情報の抽出と要約生成 (共通処理)
# ------------------------------------------------------------------

# セッションID（グループ通知用）: hook入力から抽出済みの値を優先。
# Geminiのhook入力はsession_id欠落が普通なので、フォールバックの親ディレクトリ名導出
# （derive_session_id parent-dir相当）をサブプロセスなしの純bashで行う。
# ヘルパー本体は他プラットフォーム共用のため変更しない。
if [[ -z "${session_id}" && -n "${transcript_path}" && "${transcript_path}" != "null" && "${transcript_path}" == */* ]]; then
    _parent="${transcript_path%/*}"
    session_id="${_parent##*/}"
fi
[[ -z "${session_id}" || "${session_id}" == "." ]] && session_id="default"
notification_group=$(build_notification_group "${session_id}")
debug_log "Session ID: ${session_id}, Notification group: ${notification_group}"

summary=""
session_duration_formatted=""
completion_time=""
START_TIME=""
END_TIME=""
USER_COUNT=0

if [[ -n "${transcript_path}" && "${transcript_path}" != "null" && -f "${transcript_path}" ]]; then
    debug_log "Processing transcript: ${transcript_path}"

    # トランスクリプト(JSON/JSONL)から情報を一括抽出
    eval $(jq -s -r '
      (if (length == 1 and (.[0].messages | type) == "array") then .[0].messages else . end) as $msgs |
      (if (.[0].startTime != null) then .[0].startTime else null end) as $start |
      (if (length == 1 and (.[0].messages | type) == "array") then .[0].lastUpdated else ((map(select(."$set" != null and ."$set".lastUpdated != null)) | last | ."$set".lastUpdated) // .[0].lastUpdated) end) as $end |
      ($msgs | map(select(.type == "user" and (
        ((.content | type) == "array" and .content[-1].text != null) or
        ((.displayContent | type) == "array" and .displayContent[-1].text != null) or
        ((.content | type) == "string")
      )))) as $user_msgs |
      ($user_msgs | length) as $count |
      (if $count > 0 then
        if ($user_msgs[-1].displayContent != null and ($user_msgs[-1].displayContent | type) == "array" and ($user_msgs[-1].displayContent | length) > 0) then
          $user_msgs[-1].displayContent[-1].text
        elif ($user_msgs[-1].content != null and ($user_msgs[-1].content | type) == "array" and ($user_msgs[-1].content | length) > 0) then
          $user_msgs[-1].content[-1].text
        elif ($user_msgs[-1].content | type) == "string" then
          $user_msgs[-1].content
        else
          ""
        end
       else
        ""
       end) as $last_msg |
      @sh "START_TIME=\($start) END_TIME=\($end) USER_COUNT=\($count) LAST_MSG=\($last_msg)"
    ' "${transcript_path}")

    # 時間計算
    session_duration_formatted=$(format_session_duration "${START_TIME}" "${END_TIME}")
    completion_time=$(format_completion_time_jst "${END_TIME}")

    # 要約テキスト生成（メッセージなしのセッションでは空のまま）
    # コマンド履歴っぽく見せる処理: 先頭の # /command ... のコメントマーカーを除去する
    # （旧sed版は全行の先頭#を剥がしていたが、下流のnormalize_onelineが改行を潰すため
    #   文字列先頭のみで十分。sedのサブプロセス起動も省ける）
    if [[ "${LAST_MSG}" =~ ^[[:space:]]*#[[:space:]]*(.*)$ ]]; then
        LAST_MSG="${BASH_REMATCH[1]}"
    fi

    # タスク種別推測（スラッシュコマンド→⚡は共通ヘルパー側で判定）
    task_type=$(guess_task_type_emoji "${LAST_MSG}")

    summary=$(build_session_summary "${task_type}" "${LAST_MSG}" "${USER_COUNT}" "${session_duration_formatted}")
fi

# ------------------------------------------------------------------
# イベント別処理
# ------------------------------------------------------------------

# ToolPermission 以外の notification はアイコン先行設定の時点で exit 済み
# （ACTION_DETAILは冒頭の統合jq evalで抽出済み）
if [[ "${EVENT_TYPE}" == "notification" ]]; then
    if [[ -n "${ACTION_DETAIL}" ]]; then
        MSG_BODY="${ACTION_DETAIL}"
    else
        MSG_BODY="承認が必要です"
    fi

    # 要約を追記
    if [[ -n "${summary}" ]]; then
        MSG_BODY="${MSG_BODY}"$'\n'"${summary}"
    fi

    debug_log "Sending ToolPermission notification: ${MSG_BODY}"

    notify "$(build_ai_title "⚠️" "承認待ち")" "${MSG_BODY}" "Purr" "${notification_group}"
    exit 0
fi

# after_agent の場合
notification_title=$(build_ai_title "✅" "終了")

debug_log "Sending notification: title='${notification_title}', message='${summary}'"

notify "${notification_title}" "${summary:-💭 メッセージなし}" "Purr" "${notification_group}" "${completion_time}"

# --- context逼迫アラート ---
# 最新chat JSONLの探索（旧find|stat|sort|head|cut連鎖）とトークン抽出（旧インライン
# python + jq3回 + bc）を gemini_context_usage.py の1回起動に集約。
debug_log "Evaluating Gemini context alert..."
_gemini_chat_dir="${HOME}/.gemini/tmp"
# session_idの先頭8文字（または全体）でchat JSONLを引き当て
_session_prefix="${session_id:0:8}"
if [[ -n "${_session_prefix}" && "${_session_prefix}" != "defa" && -d "${_gemini_chat_dir}" ]]; then
    GEMINI_CTX_USAGE="${SET:-$HOME/Desktop/repository/SettingFiles/}shell/tmux/gemini_context_usage.py"
    _ctx_out=$(python3 "${GEMINI_CTX_USAGE}" "${_gemini_chat_dir}" "${_session_prefix}" 2>/dev/null)
    [[ -n "${_ctx_out}" ]] && eval "${_ctx_out}"
    GEMINI_CONTEXT_TOKENS="${GEMINI_CONTEXT_TOKENS:-0}"
    GEMINI_WINDOW="${GEMINI_WINDOW:-0}"
    debug_log "Gemini context tokens: ${GEMINI_CONTEXT_TOKENS}, total tokens: ${GEMINI_TOTAL_TOKENS:-0}, model: ${GEMINI_MODEL:-}, used_pct: ${GEMINI_USED_PCT:-0.0}%"

    if [[ "${GEMINI_CONTEXT_TOKENS}" -gt 0 && "${GEMINI_WINDOW}" -gt 0 ]]; then
        source "${SET:-$HOME/Desktop/repository/SettingFiles/}shell/zsh/alias/context-alert.zsh" 2>/dev/null || true
        if declare -f ctx_alert_evaluate >/dev/null 2>&1; then
            ctx_alert_evaluate "gemini" "${session_id}" "${GEMINI_USED_PCT:-0.0}" \
                "${EMOJI_ID_GEMINI:-💎}" "${GEMINI_WINDOW}" "${GEMINI_CONTEXT_TOKENS}" \
                >/dev/null 2>&1 || true
        fi
    fi
fi

debug_log "=== Gemini Notification Hook Completed ==="
