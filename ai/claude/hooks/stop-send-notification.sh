#!/bin/bash
export LANG="${LANG:-en_US.UTF-8}"

if [[ "${HERDR_ENV:-}" == "1" ]]; then
    exit 0
fi

# 通知音はイベント種別で決まる（ai_notification_sound、共通ヘッダ経由で定義）。
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
    @sh "session_id=\(.session_id // "")"
' 2>/dev/null)"
agent_id="${agent_id:-}"
hook_event_name="${hook_event_name:-}"
transcript_path="${transcript_path:-}"
notification_type="${notification_type:-}"
notification_message="${notification_message:-}"
stop_failure_error="${stop_failure_error:-}"
session_id="${session_id:-}"

# サブエージェント由来のイベントは無視（メインエージェントの動向のみ通知）。
# agent_id はサブエージェント内で発火した場合のみ存在する（公式仕様）。
if [[ -n "${agent_id}" ]]; then
    debug_log "Subagent event detected (agent_id=${agent_id}), skipping"
    exit 0
fi

debug_log "Hook event: ${hook_event_name}"
debug_log "Transcript path extracted: ${transcript_path}"

# --- tmuxアイコン先行設定（Notification / StopFailure のみ） ---
# Mac通知とtmuxアイコンの両方をこのフックが所有する（pyフックは進行中🤖とSessionEndのみ担当）。
# アイコンは notify --tmux-icon に統合せず、イベント確定直後のここで設定する。
# notify は後続のトランスクリプト解析（要約生成、長セッションで数秒〜十数秒）の後になり、
# 統合するとアイコン表示がそのぶん遅れるため。
# バックグラウンド起動でpython3起動(数十ms)をクリティカルパスから外す。
# 後続の解析+notifyが必ず長く走るため、フック終了前にアイコン設定は完了する。
# Stopの✅は先行設定しない: バックグラウンド作業継続の判定にトランスクリプト解析が必要なため、
# 解析後（PENDING_BACKGROUND_WORKチェック通過後）に設定する。
if [[ "${hook_event_name}" == "Notification" ]]; then
    # idle_prompt（ターン終了後60秒無入力のリマインダー）は意図的に対象外。
    # 放置しただけで完了✅アイコンが✋に上書きされ、承認待ちと紛らわしいため、
    # 通知もアイコン更新もせず無視する。
    # agent_needs_input/agent_completedは claude agents（エージェントビュー）/`/bg`のバック
    # グラウンドセッションが入力待ち・完了になったときの通知（v2.1.198〜）。エージェントビュー
    # が開いている間のみ発火する制約があるが、開いていれば拾えるようにする。
    if [[ "${notification_type}" != "permission_prompt" \
       && "${notification_type}" != "elicitation_dialog" \
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

# transcriptファイルが存在するかチェック。不在ならsession_idからhost上の実transcriptを
# 探し直す（realclaudian等サンドボックス実行でtarget名前空間のパスが渡るケースの救済）。
if [[ ! -f "${transcript_path}" ]]; then
    debug_log "Transcript not found at hook-provided path: ${transcript_path}"
    recovered=$(resolve_host_transcript "${session_id}")
    if [[ -n "${recovered}" ]]; then
        debug_log "Recovered host transcript by session_id: ${recovered}"
        transcript_path="${recovered}"
    else
        debug_log "Host transcript recovery failed (session_id=${session_id})"
        hook_fallback_notify 'セッションが終了しました'
        exit 0
    fi
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
# 解析失敗時は0（作業なし）に劣化させ、通知が完全に止まる事故を避ける
PENDING_BACKGROUND_WORK="${PENDING_BACKGROUND_WORK:-0}"
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

    # 承認待ち（permission_prompt / elicitation_dialog）・
    # バックグラウンドセッション（agent_needs_input / agent_completed）でタイトルを区別する。
    # agent_completedはメイン自身のStop（✅終了）と紛らわしいため「バックグラウンド」を明示する。
    if [[ "${notification_type}" == "agent_needs_input" ]]; then
        notification_title=$(build_ai_title "🙋" "バックグラウンド入力待ち")
    elif [[ "${notification_type}" == "agent_completed" ]]; then
        notification_title=$(build_ai_title "✅" "バックグラウンド完了")
    else
        notification_title=$(build_ai_title "⚠️" "承認待ち")
    fi
    debug_log "Sending awaiting-input notification (${notification_type}): ${notification_body}"
    notify "${notification_title}" "${notification_body}" "$(ai_notification_sound waiting)" "${notification_group}"
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
    notify "$(build_ai_title "❌" "エラー停止")" "${notification_body}" "$(ai_notification_sound error)" "${notification_group}" "${COMPLETION_TIME_JST}"
    exit 0
fi

# Stopイベント: 終了通知
# Stopはターン終了ごとに発火するが、async Agentの完了待ちやScheduleWakeup武装中は
# 会話がまだ継続する（ハーネスが再起動する）ため、完了アイコン・終了通知とも送らない。
# Stop hook入力にbackground_tasks等のフィールドは存在しない（公式スキーマ・実入力とも確認済み）ため、
# transcript解析（claude_transcript_analyze.py）が判定したPENDING_BACKGROUND_WORKを用いる。
if [[ "${PENDING_BACKGROUND_WORK}" == "1" ]]; then
    debug_log "Pending background work detected, skipping stop notification"
    exit 0
fi

# ✅アイコンは解析後のここで設定する（先行設定すると作業継続中でも✅になる）。
# 直後にnotifyを呼ぶため、tmux更新は同期で完了させる（CLAUDE.mdのフック規約）。
update_tmux_window_name "${EMOJI_STATUS_COMPLETED}" "${AI_HOOK_EMOJI_ID}"

notification_title=$(build_ai_title "✅" "終了")

debug_log "Sending stop notification: title='${notification_title}', message='${summary}'"
notify "${notification_title}" "${summary:-💭 セッションが開始されましたが、メッセージはありませんでした}" "$(ai_notification_sound completed)" "${notification_group}" "${COMPLETION_TIME_JST}"

debug_log "=== Claude Notification Hook Completed ==="
