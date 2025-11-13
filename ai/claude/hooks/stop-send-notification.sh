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
                # 改行を除去してスペースに置換
                content=$(echo "${line}" | jq -r '.message.content // empty' | tr '\n' ' ' | sed 's/  */ /g')

                # slashコマンドの場合、<command-args>タグから引数を抽出
                if [[ "${content}" =~ '<command-args>'([^'<']*)'</command-args>' ]]; then
                    extracted_args="${BASH_REMATCH[1]}"
                    debug_log "Found command-args tag, extracted: '${extracted_args}'"

                    # 引数が空でない場合はそれを使用（改行も除去）
                    if [[ -n "${extracted_args}" ]]; then
                        content=$(echo "${extracted_args}" | tr '\n' ' ' | sed 's/  */ /g')
                        debug_log "Using command args as content: ${content:0:100}"
                    else
                        # 引数が空の場合、<command-name>からコマンド名を取得
                        if [[ "${BASH_REMATCH[0]}" =~ '<command-name>'([^'<']*)'</command-name>' ]] || [[ "$(echo "${line}" | jq -r '.message.content // empty')" =~ '<command-name>'([^'<']*)'</command-name>' ]]; then
                            content="${BASH_REMATCH[1]}"
                            debug_log "Using command name as content: ${content}"
                        fi
                    fi
                fi
            elif [[ "${content_type}" == "array" ]]; then
                # 配列の場合、textタイプの要素のみを抽出して結合
                content=$(echo "${line}" | jq -r '.message.content[] | select(.type == "text") | .text' | tr '\n' ' ' | sed 's/  */ /g' | sed 's/^ *//;s/ *$//')
            else
                content=""
            fi

            debug_log "Found message: role=${role}, content_type=${content_type}, content_length=${#content}"

            # システムメッセージかどうかを判定する関数
            is_system_message() {
                local msg="$1"

                # HTMLタグが含まれている
                if [[ "${msg}" =~ '<'[^'>']+'>' ]]; then
                    return 0  # true
                fi

                # Caveatで始まる
                if [[ "${msg}" =~ ^Caveat: ]]; then
                    return 0
                fi

                # コマンド説明パターン (例: "# /sc:help - Command Reference")
                if [[ "${msg}" =~ ^'#'[[:space:]]*'/'[a-z:-]+[[:space:]]*'-' ]]; then
                    return 0
                fi

                # "ARGUMENTS:"で始まる（コマンド説明の一部）
                if [[ "${msg}" =~ ^ARGUMENTS:[[:space:]] ]]; then
                    return 0
                fi

                # 空または短すぎる（10文字未満）
                if [[ ${#msg} -lt 10 ]]; then
                    return 0
                fi

                return 1  # false
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

    # timestampがnullでない最初の行を取得
    first_timestamp=$(echo "${filtered_log}" | jq -r 'select(.timestamp) | .timestamp' 2>/dev/null | grep -v '^null$' | head -1)
    # timestampがnullでない最後の行を取得
    last_timestamp=$(echo "${filtered_log}" | jq -r 'select(.timestamp) | .timestamp' 2>/dev/null | grep -v '^null$' | tail -1)

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
    if [[ -n "${session_duration_formatted}" ]]; then
        suffix=" [x${user_count}(${session_duration_formatted})]"
    else
        suffix=" [x${user_count}]"
    fi

    # 最終的な改行除去（念のため）
    first_user_message=$(echo "${first_user_message}" | tr '\n' ' ' | sed 's/  */ /g' | sed 's/^ *//;s/ *$//')
    debug_log "Final first_user_message after newline removal: ${first_user_message:0:100}"

    # メッセージとサフィックスを結合
    summary="${task_type} ${first_user_message}${suffix}"

    # 80文字を超える場合、メッセージ部分を短縮（サフィックスは保持）
    max_summary_length=80
    if [[ ${#summary} -gt ${max_summary_length} ]]; then
        # 絵文字のバイト長を考慮した計算
        # UTF-8絵文字は通常4バイト、macOSの通知システムではさらに余裕を持たせる
        emoji_display_length=2  # 絵文字の表示幅（安全マージン込み）
        space_length=1
        ellipsis_length=3  # "..." の長さ

        # サフィックスと絵文字、スペース、省略記号を除いた、メッセージに使える文字数を計算
        max_message_length=$((max_summary_length - emoji_display_length - space_length - ${#suffix} - ellipsis_length))

        debug_log "Truncating message: original_length=${#summary}, max_allowed=${max_summary_length}, max_message=${max_message_length}"

        # メッセージを切り詰め（マルチバイト文字対応）
        truncated_message=$(echo "${first_user_message}" | sed -E "s/^(.{0,${max_message_length}}).*/\1/")
        summary="${task_type} ${truncated_message}...${suffix}"

        # 最終的な長さを検証（念のため再チェック）
        final_length=${#summary}
        debug_log "Final summary length: ${final_length}"

        # まだ長すぎる場合、さらに調整
        if [[ ${final_length} -gt ${max_summary_length} ]]; then
            # 安全のため、さらに5文字短くする
            max_message_length=$((max_message_length - 5))
            truncated_message=$(echo "${first_user_message}" | sed -E "s/^(.{0,${max_message_length}}).*/\1/")
            summary="${task_type} ${truncated_message}...${suffix}"
            debug_log "Re-truncated to: ${#summary} chars"
        fi
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

# IDE判定情報を取得
detected_ide="${TERM_PROGRAM:-unknown}"

debug_log "Detected IDE: ${detected_ide}"
debug_log "Sending notification: title='${notification_title}', message='${summary}'"

# notify関数の第4引数にIDEのヒントを渡す
notify "${notification_title}" "${summary}" "Submarine" "${detected_ide}"

debug_log "=== Claude Stop Hook Completed ==="