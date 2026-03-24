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

    tmux new-window -n "cl-rvw:${current_window}" "zsh -ic 'cl-pr-review ${pr_number}; zsh'"
    tmux new-window -n "gm-rvw:${current_window}" "zsh -ic 'gm-pr-review ${pr_number}; zsh'"

    tmux select-window -t "${current_window}"
}

cl-gm-pr-review-subagents() {
    local pr_number="$1"
    if [[ -z "$pr_number" ]]; then
        echo "Usage: cl-gm-pr-review-subagents <PR番号>" >&2
        return 1
    fi

    local current_window
    current_window=$(tmux display-message -p '#W')

    tmux new-window -n "cl-rvw:${current_window}" "zsh -ic 'cl-pr-review-subagents ${pr_number}; zsh'"
    tmux new-window -n "gm-rvw:${current_window}" "zsh -ic 'gm-pr-review ${pr_number}; zsh'"

    tmux select-window -t "${current_window}"
}

ai-pr-review() {
    local pr_number="$1"
    if [[ -z "$pr_number" ]]; then
        echo "Usage: ai-pr-review <PR番号>" >&2
        return 1
    fi

    local current_window
    current_window=$(tmux display-message -p '#W')

    tmux new-window -n "cl-pr-rvw:${current_window}" "zsh -ic 'cl-pr-review ${pr_number}; zsh'"
    tmux new-window -n "cl-pr-rvw-agent:${current_window}" "zsh -ic 'cl-pr-review-subagents ${pr_number}; zsh'"
    tmux new-window -n "gm-pr-rvw:${current_window}" "zsh -ic 'gm-pr-review ${pr_number}; zsh'"

    tmux select-window -t "${current_window}"
}