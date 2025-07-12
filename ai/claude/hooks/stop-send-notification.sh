#!/bin/bash

# デバッグ用ログファイル
DEBUG_LOG="/tmp/claude-hook-debug.log"

# エラーハンドリング設定
set -e

# デバッグ関数
debug_log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "${DEBUG_LOG}"
}

debug_log "=== Claude Stop Hook Started ==="

# hookからJSONを読み取り
hook_input=$(cat)
debug_log "Hook input received: ${hook_input}"

# jqが利用可能かチェック
if ! command -v jq &> /dev/null; then
    terminal-notifier -title '🤖 Claude Code終了' -message 'jqが見つかりません' -sound Submarine
    exit 1
fi

# JSONからtranscript_pathを抽出
transcript_path=$(echo "${hook_input}" | jq -r '.transcript_path')
debug_log "Transcript path extracted: ${transcript_path}"

# transcript_pathが取得できているかチェック
if [[ -z "${transcript_path}" || "${transcript_path}" == "null" ]]; then
    debug_log "No transcript path found"
    terminal-notifier -title '🤖 Claude Code終了' -message 'transcript pathが見つかりません' -sound Submarine
    exit 0
fi

# transcriptファイルが存在するかチェック
if [[ ! -f "${transcript_path}" ]]; then
    debug_log "Transcript file not found: ${transcript_path}"
    terminal-notifier -title '🤖 Claude Code終了' -message 'セッションが終了しました' -sound Submarine
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

# タスクの種類を推測
task_type="💬 一般的な質問"
if [[ "$first_user_message" =~ (実装|コード|プログラム|関数|バグ|修正|追加|作成) ]]; then
    task_type="💻 コーディング"
elif [[ "$first_user_message" =~ (検索|調べ|探し|find|grep|確認) ]]; then
    task_type="🔍 検索・調査"
elif [[ "$first_user_message" =~ (説明|教え|解説|どう|なぜ|what|how) ]]; then
    task_type="📚 説明・学習"
elif [[ "$first_user_message" =~ (テスト|test|チェック|確認) ]]; then
    task_type="🧪 テスト・検証"
fi

# 概要を作成
if [[ ${#user_messages[@]} -gt 0 ]]; then
    # 最初のメッセージから要約を作成（80文字まで）
    first_message_short=$(echo "$first_user_message" | head -c 80)
    if [[ ${#first_user_message} -gt 80 ]]; then
        first_message_short="${first_message_short}..."
    fi

    if [[ ${#user_messages[@]} -eq 1 ]]; then
        summary="${task_type}\n${first_message_short}"
    else
        summary="${task_type} (${#user_messages[@]}回のやり取り)\n${first_message_short}"
    fi
else
    summary="💭 セッションが開始されましたが、メッセージはありませんでした"
fi

# 通知を送信
debug_log "Sending notification: title='🤖 Claude Code終了 (${total_messages}メッセージ)', message='${summary}'"
terminal-notifier \
    -title "🤖 Claude Code終了 (${total_messages}メッセージ)" \
    -message "${summary}" \
    -sound Submarine

debug_log "=== Claude Stop Hook Completed ==="