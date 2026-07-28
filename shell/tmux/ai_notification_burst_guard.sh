#!/bin/bash
# APIエラー通知のburst抑止ヘルパー（claude tmux経路・Herdr経路の両方から共有）。
# rate_limit等は同一セッション内で短時間に連発することがあり（実測: 7~40秒間隔で5連続）、
# 抑止しないと通知音（Basso）が連打される。Herdr専用の状態ディレクトリ
# （HERDR_PLUGIN_STATE_DIR）には依存せず、両経路が共有できる場所に状態を持つ。

# 状態ファイルの置き場所。呼び出し側が上書き可能（テスト用）。
_ai_notification_burst_state_dir() {
    echo "${AI_NOTIFICATION_BURST_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/ai-notification-burst}"
}

# 同一セッション・同一エラー種別の直近通知からしきい値秒以内かどうかを判定する。
# 抑止すべき（=直近通知から間もない）なら真(0)、通知してよいなら偽(1)を返す。
# fail-safe: 状態ファイルの読み書きに失敗した場合は「抑止しない」= 通知する側に倒す
# （抑止ロジックの障害で通知そのものが死ぬ事故を避けるため）。
# Usage: api_error_burst_should_suppress <session_id> <error_type> <now_epoch> <threshold_seconds>
api_error_burst_should_suppress() {
    local session_id="$1" error_type="$2" now_epoch="$3" threshold="$4"
    local state_dir state_file last_epoch

    [[ -z "${session_id}" ]] && return 1

    state_dir="$(_ai_notification_burst_state_dir)"
    mkdir -p "${state_dir}" 2>/dev/null || return 1
    [[ -w "${state_dir}" ]] || return 1

    # セッションIDとエラー種別を状態ファイル名に反映する。両方とも英数字主体だが
    # 念のため危険文字を除去してからファイル名に使う。
    local safe_id="${session_id//[^A-Za-z0-9_.-]/_}"
    local safe_error="${error_type//[^A-Za-z0-9_.-]/_}"
    state_file="${state_dir}/${safe_id}--${safe_error}.last"

    if [[ -f "${state_file}" ]]; then
        last_epoch="$(cat "${state_file}" 2>/dev/null)"
        if [[ "${last_epoch}" =~ ^[0-9]+$ ]] && (( now_epoch - last_epoch < threshold )); then
            return 0
        fi
    fi

    printf '%s' "${now_epoch}" >| "${state_file}" 2>/dev/null || return 1
    return 1
}
