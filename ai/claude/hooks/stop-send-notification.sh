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
# 小文字形を直接定義して共通ヘッダのtrフォールバック起動を省く
AI_HOOK_LABEL_LOWER='claude'

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

# hook入力の必要フィールドを1回のjqでまとめて抽出（フィールドごとのjq起動を削減）。
# 抽出失敗時はevalが空になり、直後のデフォルト代入で既存のフォールバック分岐へ劣化する。
eval "$(printf '%s' "${hook_input}" | jq -r '
    @sh "agent_id=\(.agent_id // "")",
    @sh "hook_event_name=\(.hook_event_name // "")",
    @sh "transcript_path=\(.transcript_path // "")",
    @sh "notification_type=\(.notification_type // "")",
    @sh "notification_message=\(.message // "")",
    @sh "stop_failure_error=\(.error // "")",
    @sh "session_id=\(.session_id // "")",
    @sh "running_task_count=\([(.background_tasks // [])[] | select(.status == "running")] | length)"
' 2>/dev/null)"
agent_id="${agent_id:-}"
hook_event_name="${hook_event_name:-}"
transcript_path="${transcript_path:-}"
notification_type="${notification_type:-}"
notification_message="${notification_message:-}"
stop_failure_error="${stop_failure_error:-}"
session_id="${session_id:-}"
running_task_count="${running_task_count:-0}"

# サブエージェント由来のイベントは無視（メインエージェントの動向のみ通知）。
# agent_id はサブエージェント内で発火した場合のみ存在する（公式仕様）。
if [[ -n "${agent_id}" ]]; then
    debug_log "Subagent event detected (agent_id=${agent_id}), skipping"
    exit 0
fi

debug_log "Hook event: ${hook_event_name}"
debug_log "Transcript path extracted: ${transcript_path}"

# バックグラウンドタスク（サブエージェント等）がrunning中のStop発火では、
# 実際はまだ作業中なので「完了」通知を送らずにスキップする。
# 完了済みタスクが配列に残っても誤判定しないよう、status=="running"の有無で判定する。
if [[ "${hook_event_name}" == "Stop" ]]; then
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
# バックグラウンド起動でpython3起動(数十ms)をクリティカルパスから外す。
# 後続の解析+notifyが必ず長く走るため、フック終了前にアイコン設定は完了する。
if [[ "${hook_event_name}" == "Notification" ]]; then
    # idle_prompt（応答待ち60秒経過）も通知対象。Stop通知がバックグラウンドタスク実行中で
    # 抑制された場合や承認待ち通知を見逃した場合、これが唯一のリマインダーになるため。
    # agent_needs_input/agent_completedは claude agents（エージェントビュー）/`/bg`のバック
    # グラウンドセッションが入力待ち・完了になったときの通知（v2.1.198〜）。エージェントビュー
    # が開いている間のみ発火する制約があるが、開いていれば拾えるようにする。
    if [[ "${notification_type}" != "permission_prompt" \
       && "${notification_type}" != "elicitation_dialog" \
       && "${notification_type}" != "idle_prompt" \
       && "${notification_type}" != "agent_needs_input" \
       && "${notification_type}" != "agent_completed" ]]; then
        debug_log "Notification type ${notification_type} does not require notification, exiting"
        exit 0
    fi
    if [[ "${notification_type}" == "agent_completed" ]]; then
        update_tmux_window_name "${EMOJI_STATUS_COMPLETED}" "${AI_HOOK_EMOJI_ID}" &
    else
        update_tmux_window_name "${EMOJI_STATUS_NOTIFICATION}" "${AI_HOOK_EMOJI_ID}" &
    fi
elif [[ "${hook_event_name}" == "Stop" ]]; then
    update_tmux_window_name "${EMOJI_STATUS_COMPLETED}" "${AI_HOOK_EMOJI_ID}" &
elif [[ "${hook_event_name}" == "StopFailure" ]]; then
    update_tmux_window_name "${EMOJI_STATUS_ERROR}" "${AI_HOOK_EMOJI_ID}" &
fi

# セッションID（グループ通知用）: hook入力から抽出済みの値を優先し、
# 無い場合のみ共通ヘルパーでtranscript_pathから導出する
if [[ -z "${session_id}" ]]; then
    session_id=$(derive_session_id '{}' "${transcript_path}")
fi
notification_group=$(build_notification_group "${session_id}")
debug_log "Session ID: ${session_id}, Notification group: ${notification_group}"

# transcript_pathが取得できているかチェック（集約jqがnullを空文字列に正規化済み）
if [[ -z "${transcript_path}" ]]; then
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

# 共通処理: トランスクリプト解析（単一パスPythonで要約に必要な値のみ抽出）
# 旧実装の1行ごとのjq起動＋タイムスタンプ用の全ファイル再走査を1プロセスに置き換えた
debug_log "Processing transcript for summary generation..."

CLAUDE_ANALYZE="${SET:-$HOME/Desktop/repository/SettingFiles/}shell/tmux/claude_transcript_analyze.py"
analysis=$(python3 "${CLAUDE_ANALYZE}" "${transcript_path}" 2>/dev/null)
analysis_status=$?
if [[ ${analysis_status} -eq 0 && -n "${analysis}" ]]; then
    eval "${analysis}"
else
    # 解析失敗時はゼロ値のまま進み、後段の空summaryフォールバック通知に劣化させる
    debug_log "Transcript analysis failed (status=${analysis_status})"
fi
LAST_USER_MESSAGE="${LAST_USER_MESSAGE:-}"
USER_MESSAGE_COUNT="${USER_MESSAGE_COUNT:-0}"
ASSISTANT_MESSAGE_COUNT="${ASSISTANT_MESSAGE_COUNT:-0}"
FIRST_TIMESTAMP="${FIRST_TIMESTAMP:-}"
LAST_TIMESTAMP="${LAST_TIMESTAMP:-}"
# セッション時間と完了時刻も解析スクリプトが算出済み（dateサブプロセス削減）
SESSION_DURATION_FORMATTED="${SESSION_DURATION_FORMATTED:-}"
COMPLETION_TIME_JST="${COMPLETION_TIME_JST:-}"
debug_log "Analysis: user_count=${USER_MESSAGE_COUNT}, assistant_count=${ASSISTANT_MESSAGE_COUNT}, last_msg_len=${#LAST_USER_MESSAGE}, first_ts=${FIRST_TIMESTAMP}, last_ts=${LAST_TIMESTAMP}"
debug_log "Session duration: ${SESSION_DURATION_FORMATTED}, completion time (JST): ${COMPLETION_TIME_JST}"

# タスクの種類を推測
task_type=$(guess_task_type_emoji "${LAST_USER_MESSAGE}")

# 概要を作成（メッセージなしのセッションでは空になる）
summary=$(build_session_summary "${task_type}" "${LAST_USER_MESSAGE}" "${USER_MESSAGE_COUNT}" "${SESSION_DURATION_FORMATTED}")
debug_log "Summary: ${summary}"

# --- イベント別通知 ---
# 承認が不要な notification_type はアイコン先行設定の時点で exit 済み
if [[ "${hook_event_name}" == "Notification" ]]; then
    notification_body="${notification_message}"
    # 共通処理で生成された整形済みsummaryを追記
    if [[ -n "${summary}" ]]; then
        notification_body="${notification_body}"$'\n'"${summary}"
    fi

    # 承認待ち（permission_prompt / elicitation_dialog）・入力待ち（idle_prompt）・
    # バックグラウンドセッション（agent_needs_input / agent_completed）でタイトルを区別する。
    # agent_completedはメイン自身のStop（✅終了）と紛らわしいため「バックグラウンド」を明示する。
    if [[ "${notification_type}" == "idle_prompt" ]]; then
        notification_title=$(build_ai_title "⏳" "入力待ち")
    elif [[ "${notification_type}" == "agent_needs_input" ]]; then
        notification_title=$(build_ai_title "🙋" "バックグラウンド入力待ち")
    elif [[ "${notification_type}" == "agent_completed" ]]; then
        notification_title=$(build_ai_title "✅" "バックグラウンド完了")
    else
        notification_title=$(build_ai_title "⚠️" "承認待ち")
    fi
    debug_log "Sending awaiting-input notification (${notification_type}): ${notification_body}"
    notify "${notification_title}" "${notification_body}" "Hero" "${notification_group}"
    exit 0
fi

# StopFailureイベント: エラー停止通知（パースエラー・APIエラー等でターンが中断された場合。
# Stopフックは発火しないため、この分岐がないとエラー終了が無通知になる）
if [[ "${hook_event_name}" == "StopFailure" ]]; then
    notification_body="エラー種別: ${stop_failure_error:-unknown}"
    if [[ -n "${summary}" ]]; then
        notification_body="${notification_body}"$'\n'"${summary}"
    fi

    debug_log "Sending stop-failure notification: ${notification_body}"
    notify "$(build_ai_title "❌" "エラー停止")" "${notification_body}" "Basso" "${notification_group}" "${COMPLETION_TIME_JST}"
    exit 0
fi

# Stopイベント: 終了通知
notification_title=$(build_ai_title "✅" "終了")

debug_log "Sending stop notification: title='${notification_title}', message='${summary}'"
notify "${notification_title}" "${summary:-💭 セッションが開始されましたが、メッセージはありませんでした}" "Hero" "${notification_group}" "${COMPLETION_TIME_JST}"

debug_log "=== Claude Notification Hook Completed ==="
