#!/bin/bash
export LANG="${LANG:-en_US.UTF-8}"

# 通知音設定 (変更する場合はここだけ編集)
NOTIFICATION_SOUND='Hero'

# デバッグフラグ (true/false)
DEBUG_ENABLED=false

# デバッグ用ログファイル
DEBUG_LOG="/tmp/claude-hook-debug.log"

# プラットフォーム識別（共通ヘッダの build_ai_title / hook_fallback_notify 等が参照）
AI_HOOK_LABEL='Claude'

# 共通ヘッダ: notify/絵文字定義/タイトル生成/tmuxアイコン操作の読み込みと debug_log 定義
source "${SET:-$HOME/Desktop/repository/SettingFiles/}shell/tmux/ai_notification_hook_common.sh"

# エラーハンドリング方針: set -e は使わない（共通ヘッダのコメント参照）

debug_log "=== Claude Notification Hook Started ==="
debug_log "Environment __CFBundleIdentifier='${__CFBundleIdentifier}'"

# hookからJSONを読み取り
hook_input=$(cat)
debug_log "Hook input received: ${hook_input}"

# jqが利用可能かチェック
if ! command -v jq &> /dev/null; then
    hook_fallback_notify 'jqが見つかりません'
    exit 1
fi

# サブエージェント由来のイベントは無視（メインエージェントの動向のみ通知）。
# agent_id はサブエージェント内で発火した場合のみ存在する（公式仕様）。
agent_id=$(echo "${hook_input}" | jq -r '.agent_id // empty')
if [[ -n "${agent_id}" ]]; then
    debug_log "Subagent event detected (agent_id=${agent_id}), skipping"
    exit 0
fi

# JSONからhook_event_nameとtranscript_pathを抽出
hook_event_name=$(echo "${hook_input}" | jq -r '.hook_event_name')
transcript_path=$(echo "${hook_input}" | jq -r '.transcript_path')
debug_log "Hook event: ${hook_event_name}"
debug_log "Transcript path extracted: ${transcript_path}"

# バックグラウンドタスク（サブエージェント等）がrunning中のStop発火では、
# 実際はまだ作業中なので「完了」通知を送らずにスキップする。
# 完了済みタスクが配列に残っても誤判定しないよう、status=="running"の有無で判定する。
if [[ "${hook_event_name}" == "Stop" ]]; then
    running_task_count=$(echo "${hook_input}" | jq -r '[(.background_tasks // [])[] | select(.status == "running")] | length' 2>/dev/null || echo 0)
    if [[ "${running_task_count}" -gt 0 ]] 2>/dev/null; then
        debug_log "Running background tasks detected (${running_task_count}), skipping stop notification"
        exit 0
    fi
fi

# --- tmuxアイコン先行設定 ---
# Mac通知とtmuxアイコンの両方をこのフックが所有する（pyフックは進行中🤖とSessionEndのみ担当）。
# アイコンは notify --tmux-icon に統合せず、イベント確定直後のここで設定する。
# notify は後続のトランスクリプト解析（要約生成、長セッションで数秒〜十数秒）の後になり、
# 統合するとアイコン表示がそのぶん遅れるため。
if [[ "${hook_event_name}" == "Notification" ]]; then
    notification_type=$(echo "${hook_input}" | jq -r '.notification_type')
    if [[ "${notification_type}" != "permission_prompt" && "${notification_type}" != "elicitation_dialog" ]]; then
        debug_log "Notification type ${notification_type} does not require notification, exiting"
        exit 0
    fi
    update_tmux_window_name "${EMOJI_STATUS_NOTIFICATION}" "${AI_HOOK_EMOJI_ID}"
elif [[ "${hook_event_name}" == "Stop" ]]; then
    update_tmux_window_name "${EMOJI_STATUS_COMPLETED}" "${AI_HOOK_EMOJI_ID}"
fi

# セッションIDを取得（グループ通知用）
# hook入力JSONにsession_idがあればそれを優先、なければtranscript_pathから導出
session_id=$(derive_session_id "${hook_input}" "${transcript_path}")
notification_group=$(build_notification_group "${session_id}")
debug_log "Session ID: ${session_id}, Notification group: ${notification_group}"

# transcript_pathが取得できているかチェック
if [[ -z "${transcript_path}" || "${transcript_path}" == "null" ]]; then
    debug_log "No transcript path found"
    hook_fallback_notify 'transcript pathが見つかりません'
    exit 0
fi

# transcriptファイルが存在するかチェック
if [[ ! -f "${transcript_path}" ]]; then
    debug_log "Transcript file not found: ${transcript_path}"
    hook_fallback_notify 'セッションが終了しました'
    exit 0
fi

# 共通処理: トランスクリプト解析と要約生成
debug_log "Processing transcript for summary generation..."

# 会話の概要を生成
summary=""
user_messages=()
assistant_messages=()
total_messages=0

# システムメッセージかどうかを判定する関数
is_system_message() {
    local msg="$1"

    # スラッシュコマンド（/で始まる）はユーザーの意図的な入力として扱う
    if [[ "${msg}" =~ ^/ ]]; then
        return 1  # false - not a system message
    fi

    # Claude Codeの既知システムタグのみマッチ（メッセージ先頭のみ）
    if [[ "${msg}" =~ ^[[:space:]]*'<'(command-message|command-name|command-args|local-command-caveat|local-command-stdout|system-reminder|user-prompt-submit-hook|tool-result|antml) ]]; then
        return 0  # true
    fi

    # Caveatで始まる
    if [[ "${msg}" =~ ^Caveat: ]]; then
        return 0
    fi

    # コマンド説明パターン (例: "# /command - Command Reference")
    if [[ "${msg}" =~ ^'#'[[:space:]]*'/'[a-z:-]+[[:space:]]*'-' ]]; then
        return 0
    fi

    # "ARGUMENTS:"で始まる（コマンド説明の一部）
    if [[ "${msg}" =~ ^ARGUMENTS:[[:space:]] ]]; then
        return 0
    fi

    # 日本語の短い指示を許容（4文字未満に緩和）
    if [[ ${#msg} -lt 4 ]]; then
        return 0
    fi

    return 1  # false
}

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

        # isMeta メッセージ（スラッシュコマンドの展開テキスト）をスキップ
        is_meta=$(echo "${line}" | jq -r '.isMeta // false')

        if [[ "${is_meta}" == "true" ]]; then
            debug_log "Skipping meta message"
            continue
        fi

        if [[ "${has_message}" == "true" ]]; then
            role=$(echo "${line}" | jq -r '.message.role // empty')

            # contentが文字列か配列かをチェック
            content_type=$(echo "${line}" | jq -r '.message.content | type')
            if [[ "${content_type}" == "string" ]]; then
                # 改行を除去してスペースに置換
                content=$(echo "${line}" | jq -r '.message.content // empty' | tr '\n' ' ' | sed 's/  */ /g')

                # スラッシュコマンド: command-nameタグからコマンド名を抽出
                if [[ "${content}" =~ '<command-name>'([^'<']*)'</command-name>' ]]; then
                    command_name="${BASH_REMATCH[1]}"
                    debug_log "Found command-name tag: '${command_name}'"

                    # command-argsタグから引数を抽出（存在し、かつ空でない場合）
                    if [[ "${content}" =~ '<command-args>'([^'<']*)'</command-args>' ]] && [[ -n "${BASH_REMATCH[1]}" ]]; then
                        extracted_args=$(echo "${BASH_REMATCH[1]}" | tr '\n' ' ' | sed 's/  */ /g')
                        content="${command_name} ${extracted_args}"
                        debug_log "Using command name + args as content: ${content:0:100}"
                    else
                        content="${command_name}"
                        debug_log "Using command name as content: ${content}"
                    fi
                fi
            elif [[ "${content_type}" == "array" ]]; then
                # 配列の場合、textタイプの要素のみを抽出して結合
                content=$(echo "${line}" | jq -r '.message.content[] | select(.type == "text") | .text' | tr '\n' ' ' | sed 's/  */ /g' | sed 's/^ *//;s/ *$//')
            else
                content=""
            fi

            debug_log "Found message: role=${role}, content_type=${content_type}, content_length=${#content}"

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

# 最後のユーザーメッセージを取得
last_user_message=""
if [[ ${#user_messages[@]} -gt 0 ]]; then
    last_user_message="${user_messages[${#user_messages[@]}-1]}"
fi

debug_log "Total user messages: ${#user_messages[@]}, assistant messages: ${#assistant_messages[@]}"

# セッション時間を計算
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

    session_duration_formatted=$(format_session_duration "${first_timestamp}" "${last_timestamp}")
    completion_time=$(format_completion_time_jst "${last_timestamp}")
    debug_log "Session duration: ${session_duration_formatted}, completion time (JST): ${completion_time}"
fi

# タスクの種類を推測
task_type=$(guess_task_type_emoji "${last_user_message}")

# 概要を作成（メッセージなしのセッションでは空になる）
# 配列の安全な長さチェック
user_count=0
if [[ -n "${user_messages[*]:-}" ]]; then
    user_count=${#user_messages[@]}
fi

summary=$(build_session_summary "${task_type}" "${last_user_message}" "${user_count}" "${session_duration_formatted}")
debug_log "Summary: ${summary}"

# --- イベント別通知 ---
# 承認が不要な notification_type はアイコン先行設定の時点で exit 済み
if [[ "${hook_event_name}" == "Notification" ]]; then
    message=$(echo "${hook_input}" | jq -r '.message // empty')

    notification_body="${message}"
    # 共通処理で生成された整形済みsummaryを追記
    if [[ -n "${summary}" ]]; then
        notification_body="${notification_body}"$'\n'"${summary}"
    fi

    debug_log "Sending approval notification: ${notification_body}"
    notify "$(build_ai_title "⚠️" "承認待ち")" "${notification_body}" "Hero" "${notification_group}"
    exit 0
fi

# Stopイベント: 終了通知
notification_title=$(build_ai_title "✅" "終了")

debug_log "Sending stop notification: title='${notification_title}', message='${summary}'"
notify "${notification_title}" "${summary:-💭 セッションが開始されましたが、メッセージはありませんでした}" "Hero" "${notification_group}" "${completion_time}"

debug_log "=== Claude Notification Hook Completed ==="
