#!/bin/bash

# notification関数を読み込み
source "${SET}shell/zsh/alias/notification.zsh"

# デバッグフラグ (true/false)
DEBUG_ENABLED=false

# デバッグ用ログファイル
DEBUG_LOG="/tmp/claude-hook-debug.log"

# エラーハンドリング設定（配列アクセスエラーを回避するため-eは使わない）
if [[ "${DEBUG_ENABLED}" == "true" ]]; then
    set -e
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

debug_log "=== Claude Stop Hook Started ==="

# hookからJSONを読み取り
hook_input=$(cat)
debug_log "Hook input received: ${hook_input}"

# jqが利用可能かチェック
if ! command -v jq &> /dev/null; then
    notify '🤖 Claude Code終了' 'jqが見つかりません' 'Submarine'
    exit 1
fi

# JSONからtranscript_pathを抽出
transcript_path=$(echo "${hook_input}" | jq -r '.transcript_path')
debug_log "Transcript path extracted: ${transcript_path}"

# transcript_pathが取得できているかチェック
if [[ -z "${transcript_path}" || "${transcript_path}" == "null" ]]; then
    debug_log "No transcript path found"
    notify '🤖 Claude Code終了' 'transcript pathが見つかりません' 'Submarine'
    exit 0
fi

# transcriptファイルが存在するかチェック
if [[ ! -f "${transcript_path}" ]]; then
    debug_log "Transcript file not found: ${transcript_path}"
    notify '🤖 Claude Code終了' 'セッションが終了しました' 'Submarine'
    exit 0
fi

debug_log "Transcript file found, processing messages..."

# 会話の概要を生成
summary=""
user_messages=()
assistant_messages=()
total_messages=0

# JSONLファイルを読んでメッセージを抽出
while IFS= read -r line; do
    if [[ -n "${line}" ]]; then
        # messageオブジェクトが存在するかチェック
        has_message=$(echo "${line}" | jq -r 'has("message")')
        # サイドチェーンメッセージ（Warmupなど）はスキップ
        is_sidechain=$(echo "${line}" | jq -r '.isSidechain // false')

        if [[ "${is_sidechain}" == "true" ]]; then
            debug_log "Skipping sidechain message"
            continue
        fi

        if [[ "${has_message}" == "true" ]]; then
            role=$(echo "${line}" | jq -r '.message.role // empty')

            # contentが文字列か配列かをチェック
            content_type=$(echo "${line}" | jq -r '.message.content | type')
            if [[ "${content_type}" == "string" ]]; then
                content=$(echo "${line}" | jq -r '.message.content // empty')
            elif [[ "${content_type}" == "array" ]]; then
                # 配列の場合、textタイプの要素のみを抽出して結合
                content=$(echo "${line}" | jq -r '.message.content[] | select(.type == "text") | .text' | tr '\n' ' ' | sed 's/  */ /g' | sed 's/^ *//;s/ *$//')
            else
                content=""
            fi

            debug_log "Found message: role=${role}, content_type=${content_type}, content_length=${#content}"

            if [[ "${role}" == "user" && -n "${content}" && "${content}" != "null" ]]; then
                user_messages+=("${content}")
                ((total_messages++))
                debug_log "Added user message: ${#content} chars"
            elif [[ "${role}" == "assistant" && -n "${content}" && "${content}" != "null" ]]; then
                assistant_messages+=("${content}")
                ((total_messages++))
                debug_log "Added assistant message: ${#content} chars"
            fi
        fi
    fi
done < "${transcript_path}"

# 最初のユーザーメッセージを取得
first_user_message=""
if [[ ${#user_messages[@]} -gt 0 ]]; then
    first_user_message="${user_messages[0]}"
fi

debug_log "Total user messages: ${#user_messages[@]}, assistant messages: ${#assistant_messages[@]}"

# セッション時間を計算
session_duration=""
session_duration_formatted=""
completion_time=""
if [[ -f "${transcript_path}" ]]; then
    # summaryタイプの行を除外したログデータを取得
    filtered_log=$(grep -v '"type":"summary"' "${transcript_path}")

    # 最初のタイムスタンプを取得
    first_timestamp=$(echo "${filtered_log}" | head -1 | jq -r '.timestamp // empty')
    # 最後のタイムスタンプを取得
    last_timestamp=$(echo "${filtered_log}" | tail -1 | jq -r '.timestamp // empty')

    debug_log "First timestamp: ${first_timestamp}"
    debug_log "Last timestamp: ${last_timestamp}"

    if [[ -n "${first_timestamp}" && "${first_timestamp}" != "null" && -n "${last_timestamp}" && "${last_timestamp}" != "null" ]]; then
        # ISO 8601形式のタイムスタンプをエポック秒に変換
        # macOSのdateコマンドは -j -f を使う
        start_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${first_timestamp%.*}" "+%s" 2>/dev/null)
        end_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${last_timestamp%.*}" "+%s" 2>/dev/null)

        if [[ -n "${start_epoch}" && -n "${end_epoch}" ]]; then
            session_duration=$((end_epoch - start_epoch))
            session_duration_formatted=$(format_duration ${session_duration})
            debug_log "Session duration: ${session_duration} seconds (${session_duration_formatted})"

            # 完了時刻を日本時間（JST）でフォーマット（HH:MM:SS形式）
            # UTC + 9時間 = JST
            jst_epoch=$((end_epoch + 32400))  # 32400 = 9 * 3600秒
            completion_time=$(date -r "${jst_epoch}" "+%H:%M:%S" 2>/dev/null)
            debug_log "Completion time (JST): ${completion_time}"
        fi
    fi
fi

# タスクの種類を推測
task_type="💬" # 一般的な質問
if [[ "$first_user_message" =~ (実装|コード|プログラム|関数|バグ|修正|追加|作成) ]]; then
    task_type="💻" # コーディング
elif [[ "$first_user_message" =~ (検索|調べ|探し|find|grep|確認) ]]; then
    task_type="🔍" # 検索・調査
elif [[ "$first_user_message" =~ (説明|教え|解説|どう|なぜ|what|how) ]]; then
    task_type="📚" # 説明・学習
elif [[ "$first_user_message" =~ (テスト|test|チェック|確認) ]]; then
    task_type="🧪" # テスト・検証
fi

# 概要を作成
# 配列の安全な長さチェック
user_count=0
if [[ -n "${user_messages[*]:-}" ]]; then
    user_count=${#user_messages[@]}
fi

if [[ ${user_count} -gt 0 ]]; then
    # サフィックス（統計情報）を作成
    if [[ ${user_count} -eq 1 ]]; then
        if [[ -n "${session_duration_formatted}" ]]; then
            suffix=" [x1(${session_duration_formatted})]"
        else
            suffix=""
        fi
    else
        if [[ -n "${session_duration_formatted}" ]]; then
            suffix=" [x${user_count}(${session_duration_formatted})]"
        else
            suffix=" [x${user_count}]"
        fi
    fi

    # メッセージとサフィックスを結合
    summary="${task_type} ${first_user_message}${suffix}"

    # 80文字を超える場合、メッセージ部分を短縮（サフィックスは保持）
    if [[ ${#summary} -gt 80 ]]; then
        # サフィックスと task_type を除いた、メッセージに使える文字数を計算
        max_message_length=$((80 - ${#task_type} - 1 - ${#suffix} - 3))  # -3 for "..."
        truncated_message=$(echo "${first_user_message}" | sed -E "s/^(.{0,${max_message_length}}).*/\1/")
        summary="${task_type} ${truncated_message}...${suffix}"
    fi
else
    summary="💭 セッションが開始されましたが、メッセージはありませんでした"
fi

# 通知を送信
# 通知タイトルの設定
if [[ -n "${completion_time}" ]]; then
    notification_title="🤖 Claude Code終了 at ${completion_time}"
else
    # completion_timeが取得できない場合は現在時刻を使用
    current_time=$(date "+%H:%M:%S")
    notification_title="🤖 Claude Code終了 at 🕰️${current_time}"
fi

debug_log "Sending notification: title='${notification_title}', message='${summary}'"
notify "${notification_title}" "${summary}" "Submarine"

debug_log "=== Claude Stop Hook Completed ==="