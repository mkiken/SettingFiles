#!/bin/bash

# notification関数を読み込み (SETが未定義の場合はHOMEから解決)
source "${SET:-$HOME/Desktop/repository/SettingFiles/}shell/zsh/alias/notification.zsh"

# デバッグフラグ (true/false)
DEBUG_ENABLED=true
DEBUG_LOG="/tmp/gemini-hook-debug.log"

# エラーハンドリング設定
if [[ "${DEBUG_ENABLED}" == "true" ]]; then
    set +e # デバッグ中はエラーで止まらないようにする（または必要に応じて調整）
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

# hookからJSONを読み取り
hook_input=$(cat)
debug_log "Hook input received: ${hook_input}"

# jqが利用可能かチェック
if ! command -v jq &> /dev/null; then
    debug_log "Error: jq not found"
    notify '🤖 Gemini CLI終了' 'jqが見つかりません' 'Submarine'
    exit 1
fi

# JSONからtranscript_pathを抽出
transcript_path=$(echo "${hook_input}" | jq -r '.transcript_path')
debug_log "Transcript path extracted: ${transcript_path}"

# transcript_pathが取得できているかチェック
if [[ -z "${transcript_path}" || "${transcript_path}" == "null" ]]; then
    debug_log "No transcript path found"
    notify '🤖 Gemini CLI終了' 'transcript pathが見つかりません' 'Submarine'
    exit 0
fi

# transcriptファイルが存在するかチェック
if [[ ! -f "${transcript_path}" ]]; then
    debug_log "Transcript file not found: ${transcript_path}"
    notify '🤖 Gemini CLI終了' 'セッションログが見つかりません' 'Submarine'
    exit 0
fi

debug_log "Transcript file found, processing..."

# トランスクリプト(JSON)から情報を一括抽出
# GeminiのtranscriptはJSONLではなく単一のJSONオブジェクトであることを想定
# .messages[] .type == "user" | "assistant"
# .startTime, .lastUpdated
eval $(jq -r '
  .startTime as $start |
  .lastUpdated as $end |
  (.messages | map(select(.type == "user"))) as $user_msgs |
  ($user_msgs | length) as $count |
  ($user_msgs[0].content // "") as $first_msg |
  @sh "START_TIME=\($start) END_TIME=\($end) USER_COUNT=\($count) FIRST_MSG=\($first_msg)"
' "${transcript_path}")

debug_log "Extracted info: START_TIME=${START_TIME}, END_TIME=${END_TIME}, USER_COUNT=${USER_COUNT}"

# セッション時間を計算
session_duration_formatted=""
completion_time=""

if [[ -n "${START_TIME}" && "${START_TIME}" != "null" && -n "${END_TIME}" && "${END_TIME}" != "null" ]]; then
    # ISO 8601形式のタイムスタンプをエポック秒に変換
    # macOSのdateコマンド (BSD date) を使用
    # ミリ秒部分(.xxxZ)を除去してパースする
    start_str="${START_TIME%.*}"
    end_str="${END_TIME%.*}"
    
    start_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${start_str}" "+%s" 2>/dev/null)
    end_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${end_str}" "+%s" 2>/dev/null)

    if [[ -n "${start_epoch}" && -n "${end_epoch}" ]]; then
        session_duration=$((end_epoch - start_epoch))
        session_duration_formatted=$(format_duration ${session_duration})
        debug_log "Session duration: ${session_duration} seconds (${session_duration_formatted})"

        # 完了時刻を日本時間（JST）でフォーマット
        # UTC + 9時間 = JST (32400秒)
        jst_epoch=$((end_epoch + 32400))
        completion_time=$(date -r "${jst_epoch}" "+%H:%M:%S" 2>/dev/null)
        debug_log "Completion time (JST): ${completion_time}"
    fi
fi

# 概要を作成
summary=""
if [[ ${USER_COUNT} -gt 0 ]]; then
    # コマンド展開されたプロンプト（"# /"で始まるもの）の汎用的な処理
    # 例: "# /sg:design - ..." のようなヘッダーで始まり、末尾にユーザー入力がある場合
    if echo "${FIRST_MSG}" | grep -q "^[[:space:]]*# /"; then
        # ヘッダーからコマンド名（例: /sg:design）を抽出
        cmd_name=$(echo "${FIRST_MSG}" | grep "^[[:space:]]*# /" | head -n 1 | awk '{print $2}')
        
        # 最後の空行以外の行を抽出（ユーザー入力と仮定）
        last_line=$(echo "${FIRST_MSG}" | grep -v "^[[:space:]]*$" | tail -n 1)
        
        # last_lineが取得でき、かつヘッダー行そのものでない場合
        if [[ -n "${last_line}" && "${last_line}" != *"# /"* ]]; then
             # ユーザー入力行にコマンド名が含まれていればそのまま、なければ付与
             if [[ "${last_line}" == *"${cmd_name}"* ]]; then
                 FIRST_MSG="${last_line}"
             else
                 FIRST_MSG="${cmd_name} ${last_line}"
             fi
        fi
    fi

    # タスクの種類を推測
    task_type="💬" # 一般的な質問
    if [[ "${FIRST_MSG}" == *"/sg:design"* ]]; then
        task_type="🎨" # Design
    elif [[ "${FIRST_MSG}" == *"/sg:analyze"* ]]; then
        task_type="📊" # Analyze
    elif [[ "${FIRST_MSG}" == *"/sg:"* ]]; then
        task_type="⚡" # Generic SuperGemini
    elif [[ "${FIRST_MSG}" =~ (実装|コード|プログラム|関数|バグ|修正|追加|作成) ]]; then
        task_type="💻" # コーディング
    elif [[ "${FIRST_MSG}" =~ (検索|調べ|探し|find|grep|確認) ]]; then
        task_type="🔍" # 検索・調査
    elif [[ "${FIRST_MSG}" =~ (説明|教え|解説|どう|なぜ|what|how) ]]; then
        task_type="📚" # 説明・学習
    elif [[ "${FIRST_MSG}" =~ (テスト|test|チェック|確認) ]]; then
        task_type="🧪" # テスト・検証
    fi

    # サフィックス（統計情報）を作成
    if [[ -n "${session_duration_formatted}" ]]; then
        suffix=" [x${USER_COUNT}(${session_duration_formatted})]"
    else
        suffix=" [x${USER_COUNT}]"
    fi

    # 改行を除去してスペースに置換
    clean_msg=$(echo "${FIRST_MSG}" | tr '\n' ' ' | sed 's/  */ /g' | sed 's/^ *//;s/ *$//')
    
    # メッセージとサフィックスを結合
    summary="${task_type} ${clean_msg}${suffix}"

    # 長さ制限処理
    max_summary_length=80
    if [[ ${#summary} -gt ${max_summary_length} ]]; then
        emoji_display_length=2
        space_length=1
        ellipsis_length=3
        
        # サフィックス分を除いた許容文字数
        max_message_length=$((max_summary_length - emoji_display_length - space_length - ${#suffix} - ellipsis_length))
        
        # 切り詰め
        truncated_message=$(echo "${clean_msg}" | sed -E "s/^(.{0,${max_message_length}}).*/\1/")
        summary="${task_type} ${truncated_message}...${suffix}"
        
        # 再チェック
        if [[ ${#summary} -gt ${max_summary_length} ]]; then
             max_message_length=$((max_message_length - 5))
             truncated_message=$(echo "${clean_msg}" | sed -E "s/^(.{0,${max_message_length}}).*/\1/")
             summary="${task_type} ${truncated_message}...${suffix}"
        fi
    fi
else
    summary="💭 セッションが開始されましたが、メッセージはありませんでした"
fi

# 通知タイトルの設定
notification_title="🤖 Gemini CLI終了"
if [[ -n "${completion_time}" ]]; then
    notification_title="${notification_title} at ${completion_time}"
else
    current_time=$(date "+%H:%M:%S")
    notification_title="${notification_title} at 🕰️${current_time}"
fi

debug_log "Sending notification: title='${notification_title}', message='${summary}'"

# notify関数を呼び出し
notify "${notification_title}" "${summary}" "Submarine"

debug_log "=== Gemini Notification Hook Completed ==="