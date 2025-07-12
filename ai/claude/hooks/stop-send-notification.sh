#!/bin/bash

# エラーハンドリング設定
set -e

# hookからJSONを読み取り
hook_input=$(cat)

# jqが利用可能かチェック
if ! command -v jq &> /dev/null; then
    terminal-notifier -title '🤖 Claude Code終了' -message 'jqが見つかりません' -sound Submarine
    exit 1
fi

# JSONからtranscript_pathを抽出
transcript_path=$(echo "${hook_input}" | jq -r '.transcript_path')

# transcript_pathが取得できているかチェック
if [[ -z "${transcript_path}" || "${transcript_path}" == "null" ]]; then
    terminal-notifier -title '🤖 Claude Code終了' -message 'transcript pathが見つかりません' -sound Submarine
    exit 0
fi

# transcriptファイルが存在するかチェック
if [[ ! -f "${transcript_path}" ]]; then
    terminal-notifier -title '🤖 Claude Code終了' -message 'セッションが終了しました' -sound Submarine
    exit 0
fi

# 会話の概要を生成
summary=""
user_messages=()
assistant_messages=()
total_messages=0

# JSONLファイルを読んでメッセージを抽出
while IFS= read -r line; do
    if [[ -n "$line" ]]; then
        role=$(echo "$line" | jq -r '.role // empty')
        content=$(echo "$line" | jq -r '.content // empty')
        
        if [[ "$role" == "user" && -n "$content" ]]; then
            user_messages+=("$content")
            ((total_messages++))
        elif [[ "$role" == "assistant" && -n "$content" ]]; then
            assistant_messages+=("$content")
            ((total_messages++))
        fi
    fi
done < "$transcript_path"

# 最初と最後のユーザーメッセージを取得
first_user_message=""
last_user_message=""
if [[ ${#user_messages[@]} -gt 0 ]]; then
    first_user_message="${user_messages[0]}"
    last_user_message="${user_messages[-1]}"
fi

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
terminal-notifier \
    -title "🤖 Claude Code終了 (${total_messages}メッセージ)" \
    -message "$summary" \
    -sound Submarine