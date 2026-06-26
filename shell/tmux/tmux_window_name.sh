#!/bin/bash
# tmuxウィンドウ名の絵文字プレフィックス操作ヘルパー
# Usage: source this file, then call update_tmux_window_name "✋",
# add_tmux_context_alert_badge, remove_tmux_context_alert_badge, or remove_tmux_window_icon

_TMUX_WINDOW_NAME_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
source "${_TMUX_WINDOW_NAME_DIR}/tmux_emoji.conf"

# tmuxセッション内かどうかを判定してpane_idを返す
# VSCode等からTMUX_PANEが継承されるケースを除外するためTERM_PROGRAM==tmuxも確認
_get_tmux_pane_id_for_window_name() {
    [[ -z "${TMUX_PANE}" || "${TERM_PROGRAM:-}" != "tmux" ]] && return 1
    echo "${TMUX_PANE}"
}

# 指定した絵文字ステータスをtmuxウィンドウ名のプレフィックスに設定する
# Usage: update_tmux_window_name "✋"
update_tmux_window_name() {
    local status_emoji="$1"
    local pane_id
    pane_id=$(_get_tmux_pane_id_for_window_name) || return 0
    local current_name
    current_name=$(tmux display-message -p -t "${pane_id}" "#W" 2>/dev/null) || return 0
    local window_id
    window_id=$(tmux display-message -p -t "${pane_id}" "#{window_id}" 2>/dev/null) || return 0
    local stripped
    stripped=$(python3 "${_TMUX_WINDOW_NAME_DIR}/tmux_emoji.py" "${current_name}") || stripped="${current_name}"
    local prefix="${current_name%"${stripped}"}"
    local context_badge=""
    [[ "${prefix}" == *"${EMOJI_CONTEXT_ALERT}"* ]] && context_badge="${EMOJI_CONTEXT_ALERT}"
    tmux rename-window -t "${window_id}" "${status_emoji}${context_badge}${stripped}" 2>/dev/null || true
}

# context逼迫バッジを状態アイコンとは独立して追加する
add_tmux_context_alert_badge() {
    local pane_id
    pane_id=$(_get_tmux_pane_id_for_window_name) || return 0
    local current_name
    current_name=$(tmux display-message -p -t "${pane_id}" "#W" 2>/dev/null) || return 0
    local window_id
    window_id=$(tmux display-message -p -t "${pane_id}" "#{window_id}" 2>/dev/null) || return 0
    local stripped
    stripped=$(python3 "${_TMUX_WINDOW_NAME_DIR}/tmux_emoji.py" "${current_name}") || stripped="${current_name}"
    local prefix="${current_name%"${stripped}"}"
    [[ "${prefix}" == *"${EMOJI_CONTEXT_ALERT}"* ]] && return 0
    tmux rename-window -t "${window_id}" "${prefix}${EMOJI_CONTEXT_ALERT}${stripped}" 2>/dev/null || true
}

# context逼迫バッジだけを外し、AI状態アイコンは残す
remove_tmux_context_alert_badge() {
    local pane_id
    pane_id=$(_get_tmux_pane_id_for_window_name) || return 0
    local current_name
    current_name=$(tmux display-message -p -t "${pane_id}" "#W" 2>/dev/null) || return 0
    local window_id
    window_id=$(tmux display-message -p -t "${pane_id}" "#{window_id}" 2>/dev/null) || return 0
    local stripped
    stripped=$(python3 "${_TMUX_WINDOW_NAME_DIR}/tmux_emoji.py" "${current_name}") || stripped="${current_name}"
    local prefix="${current_name%"${stripped}"}"
    [[ "${prefix}" != *"${EMOJI_CONTEXT_ALERT}"* ]] && return 1
    local new_prefix="${prefix/"${EMOJI_CONTEXT_ALERT}"/}"
    tmux rename-window -t "${window_id}" "${new_prefix}${stripped}" 2>/dev/null || true
}

# tmuxウィンドウ名アイコン削除の失敗理由を出力する
_report_tmux_window_icon_cleanup_status() {
    local cleanup_status="$1"

    case "${cleanup_status}" in
        2)
            echo "tmux window icon cleanup skipped: TMUX_PANE is unset or TERM_PROGRAM is not tmux" >&2
            ;;
        3)
            echo "tmux window icon cleanup failed: could not read current tmux window name" >&2
            ;;
        4)
            echo "tmux window icon cleanup failed: could not resolve tmux window id" >&2
            ;;
        5)
            echo "tmux window icon cleanup failed: could not strip emoji prefix" >&2
            ;;
        6)
            echo "tmux window icon cleanup failed: could not rename tmux window" >&2
            ;;
        *)
            echo "tmux window icon cleanup failed: unexpected status ${cleanup_status}" >&2
            ;;
    esac
}

# tmuxウィンドウ名から絵文字プレフィックスを除去して元の名前に戻す
remove_tmux_window_icon() {
    local report_error="${1:-false}"
    local pane_id
    pane_id=$(_get_tmux_pane_id_for_window_name) || {
        local cleanup_status=2
        [[ "${report_error}" == "true" ]] && _report_tmux_window_icon_cleanup_status "${cleanup_status}"
        return "${cleanup_status}"
    }
    local current_name
    current_name=$(tmux display-message -p -t "${pane_id}" "#W" 2>/dev/null) || {
        local cleanup_status=3
        [[ "${report_error}" == "true" ]] && _report_tmux_window_icon_cleanup_status "${cleanup_status}"
        return "${cleanup_status}"
    }
    local window_id
    window_id=$(tmux display-message -p -t "${pane_id}" "#{window_id}" 2>/dev/null) || {
        local cleanup_status=4
        [[ "${report_error}" == "true" ]] && _report_tmux_window_icon_cleanup_status "${cleanup_status}"
        return "${cleanup_status}"
    }
    local stripped
    stripped=$(python3 "${_TMUX_WINDOW_NAME_DIR}/tmux_emoji.py" "${current_name}") || {
        local cleanup_status=5
        [[ "${report_error}" == "true" ]] && _report_tmux_window_icon_cleanup_status "${cleanup_status}"
        return "${cleanup_status}"
    }
    [[ "${stripped}" == "${current_name}" ]] && return 1
    tmux rename-window -t "${window_id}" "${stripped}" 2>/dev/null || {
        local cleanup_status=6
        [[ "${report_error}" == "true" ]] && _report_tmux_window_icon_cleanup_status "${cleanup_status}"
        return "${cleanup_status}"
    }
    return 0
}
