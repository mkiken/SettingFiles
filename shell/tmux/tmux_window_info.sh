#!/bin/bash
# Get tmux window number label (e.g. "[W3]") or empty string if not in tmux.
# Guards against VSCode inheriting TMUX_PANE by checking TERM_PROGRAM.
get_tmux_window_label() {
    local pane_id="${TMUX_PANE}"
    [[ -z "${pane_id}" ]] && echo "" && return
    [[ "${TERM_PROGRAM:-}" != "tmux" ]] && echo "" && return
    local win_index
    win_index=$(tmux display-message -p -t "${pane_id}" "#{window_index}" 2>/dev/null)
    [[ -n "${win_index}" ]] && echo " #${win_index}" || echo ""
}
