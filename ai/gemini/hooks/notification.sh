#!/bin/bash

# notification関数を読み込み (SETが未定義の場合はHOMEから解決)
source "${SET:-$HOME/Desktop/repository/SettingFiles/}shell/zsh/alias/notification.zsh"

# デバッグフラグ (true/false)
DEBUG_ENABLED=true
DEBUG_LOG="/tmp/gemini-hook-debug.log"

# エラーハンドリング設定
if [[ "${DEBUG_ENABLED}" == "true" ]]; then
    set +e # デバッグ中はエラーで止まらないようにする
fi

# デバッグ関数
debug_log() {
    if [[ "${DEBUG_ENABLED}" == "true" ]]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "${DEBUG_LOG}"
    fi
}

# 秒数を人間が読みやすい形式に変換する関数
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
    notify '🤖 Gemini CLI終了' 'jqが見つかりません' 'Submarine'
    exit 1
fi

# ------------------------------------------------------------------
# トランスクリプト情報の抽出と要約生成 (共通処理)
# ------------------------------------------------------------------

# JSONからtranscript_pathを抽出
transcript_path=$(echo "${hook_input}" | jq -r '.transcript_path')
summary=""
session_duration_formatted=""
completion_time=""
START_TIME=""
END_TIME=""
USER_COUNT=0

if [[ -n "${transcript_path}" && "${transcript_path}" != "null" && -f "${transcript_path}" ]]; then
    debug_log "Processing transcript: ${transcript_path}"

    # トランスクリプト(JSON)から情報を一括抽出
    eval $(jq -r '
      .startTime as $start |
      .lastUpdated as $end |
      (.messages | map(select(.type == "user"))) as $user_msgs |
      ($user_msgs | length) as $count |
      ($user_msgs[0].content // "") as $first_msg |
      @sh "START_TIME=\($start) END_TIME=\($end) USER_COUNT=\($count) FIRST_MSG=\($first_msg)"
    ' "${transcript_path}")

    # 時間計算
    if [[ -n "${START_TIME}" && "${START_TIME}" != "null" && -n "${END_TIME}" && "${END_TIME}" != "null" ]]; then
        start_str="${START_TIME%.*}"
        end_str="${END_TIME%.*}"

        start_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${start_str}" "+%s" 2>/dev/null)
        end_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${end_str}" "+%s" 2>/dev/null)

        if [[ -n "${start_epoch}" && -n "${end_epoch}" ]]; then
            session_duration=$((end_epoch - start_epoch))
            session_duration_formatted=$(format_duration ${session_duration})

            # 完了時刻 (JST)
            jst_epoch=$((end_epoch + 32400))
            completion_time=$(date -r "${jst_epoch}" "+%H:%M:%S" 2>/dev/null)
        fi
    fi

    # 要約テキスト生成
    if [[ ${USER_COUNT} -gt 0 ]]; then
        # コマンド展開プロンプトの処理
        if echo "${FIRST_MSG}" | grep -q "^[[:space:]]*# /"; then
            cmd_name=$(echo "${FIRST_MSG}" | grep "^[[:space:]]*# /" | head -n 1 | sed 's/^[[:space:]]*#[[:space:]]*//')
            last_line=$(echo "${FIRST_MSG}" | grep -v "^[[:space:]]*$" | tail -n 1)
            if [[ -n "${last_line}" && "${last_line}" != *"# /"* ]]; then
                 if [[ "${last_line}" == *"${cmd_name}"* ]]; then
                     FIRST_MSG="${last_line}"
                 else
                     # コマンドに行内引数が含まれている場合（スペースがある場合）は、
                     # プロンプト末尾のテキスト（last_line）を結合せず、コマンド行を優先する
                     if [[ "${cmd_name}" =~ [[:space:]] ]]; then
                         FIRST_MSG="${cmd_name}"
                     else
                         FIRST_MSG="${cmd_name} ${last_line}"
                     fi
                 fi
            fi
        fi

        # タスク種別推測とメッセージ整形
        task_type="💬"
        msg_source="${FIRST_MSG}"

        if [[ "${FIRST_MSG}" == *"/sg:design"* ]]; then
            task_type="🎨"
            msg_source=$(echo "${FIRST_MSG}" | sed -E 's|.*\/sg:design[[:space:]]*||')
        elif [[ "${FIRST_MSG}" == *"/sg:analyze"* ]]; then
            task_type="📊"
            msg_source=$(echo "${FIRST_MSG}" | sed -E 's|.*\/sg:analyze[[:space:]]*||')
        elif [[ "${FIRST_MSG}" == *"/sg:"* ]]; then
            task_type="⚡"
            msg_source=$(echo "${FIRST_MSG}" | sed -E 's|.*\/sg:[^[:space:]]+[[:space:]]*||')
        elif [[ "${FIRST_MSG}" =~ (実装|コード|プログラム|関数|バグ|修正|追加|作成) ]]; then task_type="💻"
        elif [[ "${FIRST_MSG}" =~ (検索|調べ|探し|find|grep|確認) ]]; then task_type="🔍"
        elif [[ "${FIRST_MSG}" =~ (説明|教え|解説|どう|なぜ|what|how) ]]; then task_type="📚"
        elif [[ "${FIRST_MSG}" =~ (テスト|test|チェック|確認) ]]; then task_type="🧪"
        fi

        # メッセージが空の場合のフォールバック
        if [[ -z "${msg_source// }" ]]; then
             msg_source="${FIRST_MSG}"
        fi

        # サフィックス
        if [[ -n "${session_duration_formatted}" ]]; then
            suffix=" [x${USER_COUNT}(${session_duration_formatted})]"
        else
            suffix=" [x${USER_COUNT}]"
        fi

        clean_msg=$(echo "${msg_source}" | tr '\n' ' ' | sed 's/  */ /g' | sed 's/^ *//;s/ *$//')
        summary="${task_type} ${clean_msg}${suffix}"

        # 長さ制限
        max_summary_length=80
        if [[ ${#summary} -gt ${max_summary_length} ]]; then
            emoji_display_length=2
            space_length=1
            ellipsis_length=3
            max_message_length=$((max_summary_length - emoji_display_length - space_length - ${#suffix} - ellipsis_length))
            truncated_message=$(echo "${clean_msg}" | sed -E "s/^(.{0,${max_message_length}}).*/\1/")
            summary="${task_type} ${truncated_message}...${suffix}"
            if [[ ${#summary} -gt ${max_summary_length} ]]; then
                 max_message_length=$((max_message_length - 5))
                 truncated_message=$(echo "${clean_msg}" | sed -E "s/^(.{0,${max_message_length}}).*/\1/")
                 summary="${task_type} ${truncated_message}...${suffix}"
            fi
        fi
    fi
fi

if [[ -z "${summary}" ]]; then
    summary="💭 メッセージなし"
fi

# ------------------------------------------------------------------
# イベント別処理
# ------------------------------------------------------------------

if [[ "${EVENT_TYPE}" == "notification" ]]; then
    NOTIFICATION_TYPE=$(echo "${hook_input}" | jq -r '.notification_type // ""')

    if [[ "${NOTIFICATION_TYPE}" == "ToolPermission" ]]; then
        TOOL_NAME=$(echo "${hook_input}" | jq -r '.details.tool_name // .details.rootCommand // ""')

        if [[ -n "${TOOL_NAME}" ]]; then
            MSG_BODY="ユーザーの承認が必要です: ${TOOL_NAME}"
        else
            MSG_BODY="ユーザーの承認が必要です"
        fi

        # 要約を追記
        if [[ "${summary}" != "💭 メッセージなし" ]]; then
            MSG_BODY="${MSG_BODY}"$'\n'"${summary}"
        fi

        debug_log "Sending ToolPermission notification: ${MSG_BODY}"

        current_time=$(date "+%H:%M:%S")
        notify "🤖 Gemini CLI承認待ち at 🕰️${current_time}" "${MSG_BODY}" "Glass"
    else
        debug_log "Ignoring notification type: ${NOTIFICATION_TYPE}"
    fi
    exit 0
fi

# after_agent の場合
notification_title="🤖 Gemini CLI終了"
if [[ -n "${completion_time}" ]]; then
    notification_title="${notification_title} at ${completion_time}"
else
    current_time=$(date "+%H:%M:%S")
    notification_title="${notification_title} at 🕰️${current_time}"
fi

debug_log "Sending notification: title='${notification_title}', message='${summary}'"

notify "${notification_title}" "${summary}" "Submarine"

debug_log "=== Gemini Notification Hook Completed ==="