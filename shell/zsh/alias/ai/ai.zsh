#!/bin/zsh
# AI cross-tool aliases

cl-gm-pr-review() {
    local pr_number="$1"
    if [[ -z "$pr_number" ]]; then
        echo "Usage: cl-gm-pr-review <PR番号>" >&2
        return 1
    fi

    local current_window
    current_window=$(tmux display-message -p '#W')

    tmux new-window -n "cl-pr-review:${current_window}" "zsh -ic 'cl-pr-review ${pr_number}; zsh'"
    tmux new-window -n "gm-pr-review:${current_window}" "zsh -ic 'gm-pr-review ${pr_number}; zsh'"

    tmux select-window -t "${current_window}"
}
