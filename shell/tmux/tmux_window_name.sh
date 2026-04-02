#!/bin/bash
# tmuxウィンドウ名の絵文字プレフィックス操作ヘルパー
# Usage: source this file, then call update_tmux_window_name "✋" or remove_tmux_window_icon

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
    # 既存の絵文字プレフィックスを除去してから新しいものを付与
    local stripped
    stripped=$(python3 "${_TMUX_WINDOW_NAME_DIR}/tmux_emoji.py" "${current_name}") || stripped="${current_name}"
    tmux rename-window -t "${window_id}" "${status_emoji}${stripped}" 2>/dev/null || true
}

# tmuxウィンドウ名から絵文字プレフィックスを除去して元の名前に戻す
remove_tmux_window_icon() {
    local pane_id
    pane_id=$(_get_tmux_pane_id_for_window_name) || return 0
    local current_name
    current_name=$(tmux display-message -p -t "${pane_id}" "#W" 2>/dev/null) || return 0
    local window_id
    window_id=$(tmux display-message -p -t "${pane_id}" "#{window_id}" 2>/dev/null) || return 0
    local stripped
    stripped=$(python3 "${_TMUX_WINDOW_NAME_DIR}/tmux_emoji.py" "${current_name}") || return 0
    [[ "${stripped}" != "${current_name}" ]] && tmux rename-window -t "${window_id}" "${stripped}" 2>/dev/null || true
}
