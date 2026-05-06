#!/bin/bash
# Get tmux session/window label (e.g. " 🖥️0:3") or empty string if not in tmux.
# Guards against VSCode inheriting TMUX_PANE by checking TERM_PROGRAM.
get_tmux_label() {
    local pane_id="${TMUX_PANE}"
    [[ -z "${pane_id}" ]] && echo "" && return
    [[ "${TERM_PROGRAM:-}" != "tmux" ]] && echo "" && return
    local label
    label=$(tmux display-message -p -t "${pane_id}" '#{s/[$]//:session_id}:#{window_index}' 2>/dev/null)
    [[ -n "${label}" ]] && echo " 🖥️${label}" || echo ""
}
