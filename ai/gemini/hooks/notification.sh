#!/bin/bash

# notification関数を読み込み (SETが未定義の場合はHOMEから解決)
source "${SET:-$HOME/Desktop/repository/SettingFiles/}shell/zsh/alias/notification.zsh"
# 絵文字アイコン定義を読み込み
source "${SET:-$HOME/Desktop/repository/SettingFiles/}shell/tmux/tmux_emoji.conf"

# デバッグフラグ (true/false)
DEBUG_ENABLED=false
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
    notify "${EMOJI_ID_GEMINI}🤖 Gemini終了" 'jqが見つかりません' 'Submarine'
    exit 1
fi

# ------------------------------------------------------------------
# トランスクリプト情報の抽出と要約生成 (共通処理)
# ------------------------------------------------------------------

# JSONからtranscript_pathを抽出
transcript_path=$(echo "${hook_input}" | jq -r '.transcript_path')

# セッションIDを取得（グループ通知用）
session_id=$(echo "${hook_input}" | jq -r '.session_id // empty')
if [[ -z "${session_id}" && -n "${transcript_path}" && "${transcript_path}" != "null" ]]; then
    # Geminiの場合、transcript_pathは .../<uuid>/transcript.json となることが多いので親ディレクトリ名を使う
    session_id=$(basename "$(dirname "${transcript_path}")")
fi
if [[ -z "${session_id}" || "${session_id}" == "." ]]; then
    session_id="default"
fi
notification_group="gemini-${session_id}"
debug_log "Session ID: ${session_id}, Notification group: ${notification_group}"

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
        # コマンド履歴っぽく見せる処理（コメントアウトされたコマンド部分の除去など）
        # 簡易的に、先頭の # /command ... を除去したりする
        LAST_MSG=$(echo "${LAST_MSG}" | sed 's/^[[:space:]]*#[[:space:]]*//')

        # タスク種別推測
        task_type="💬"

        # キーワードによるアイコンの出し分け
        if [[ "${LAST_MSG}" =~ ^\/ ]]; then task_type="⚡" # スラッシュコマンド
        elif [[ "${LAST_MSG}" =~ (実装|コード|プログラム|関数|バグ|修正|追加|作成) ]]; then task_type="💻"
        elif [[ "${LAST_MSG}" =~ (検索|調べ|探し|find|grep|確認) ]]; then task_type="🔍"
        elif [[ "${LAST_MSG}" =~ (説明|教え|解説|どう|なぜ|what|how) ]]; then task_type="📚"
        elif [[ "${LAST_MSG}" =~ (テスト|test|チェック|確認) ]]; then task_type="🧪"
        fi

        # サフィックス
        if [[ -n "${session_duration_formatted}" ]]; then
            suffix=" [x${USER_COUNT}(${session_duration_formatted})]"
        else
            suffix=" [x${USER_COUNT}]"
        fi

        # 改行を削除して1行にする
        clean_msg=$(echo "${LAST_MSG}" | tr '\n' ' ' | sed 's/  */ /g' | sed 's/^ *//;s/ *$//')
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
        ACTION_DETAIL=$(echo "${hook_input}" | jq -r '
            .details |
            if (.type == "exec") then
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
        ')

        if [[ -n "${ACTION_DETAIL}" ]]; then
            MSG_BODY="${ACTION_DETAIL}"
        else
            MSG_BODY="承認が必要です"
        fi

        # 要約を追記
        if [[ "${summary}" != "💭 メッセージなし" ]]; then
            MSG_BODY="${MSG_BODY}"$'\n'"${summary}"
        fi

        debug_log "Sending ToolPermission notification: ${MSG_BODY}"

        current_time=$(date "+%H:%M:%S")
        notify "${EMOJI_ID_GEMINI}⚠️ Gemini承認待ち at 🕰️${current_time}" "${MSG_BODY}" "Glass" "${notification_group}"
    else
        debug_log "Ignoring notification type: ${NOTIFICATION_TYPE}"
    fi
    exit 0
fi

# after_agent の場合
notification_title="${EMOJI_ID_GEMINI}✅ Gemini終了"
if [[ -n "${completion_time}" ]]; then
    notification_title="${notification_title} at ${completion_time}"
else
    current_time=$(date "+%H:%M:%S")
    notification_title="${notification_title} at 🕰️${current_time}"
fi

debug_log "Sending notification: title='${notification_title}', message='${summary}'"

notify "${notification_title}" "${summary}" "Submarine" "${notification_group}"

debug_log "=== Gemini Notification Hook Completed ==="
