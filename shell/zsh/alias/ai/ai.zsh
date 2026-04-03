#!/bin/zsh
# AI cross-tool aliases

# rename-window-git.sh を呼んで git ベースのウィンドウ名を計算し、🔍プレフィックス付きで返す
_review_window_name() {
    local set_dir="${SET:-$HOME/Desktop/repository/SettingFiles}"
    source "${set_dir}/shell/tmux/tmux_emoji.conf"
    "${set_dir}/shell/tmux/rename-window-git.sh"
    local git_name
    git_name=$(tmux display-message -p '#W')
    echo "${EMOJI_STATUS_REVIEW}${git_name}"
}

cl-gm-pr-review() {
    local pr_number="$1"
    if [[ -z "$pr_number" ]]; then
        echo "Usage: cl-gm-pr-review <PR番号>" >&2
        return 1
    fi

    local review_name
    review_name=$(_review_window_name)

    tmux new-window -n "${review_name}" "zsh -ic 'gm-pr-review ${pr_number}; zsh'"

    tmux rename-window "${review_name}"
    cl-pr-review "${pr_number}"
}

cl-gm-pr-review-subagents() {
    local pr_number="$1"
    if [[ -z "$pr_number" ]]; then
        echo "Usage: cl-gm-pr-review-subagents <PR番号>" >&2
        return 1
    fi

    local review_name
    review_name=$(_review_window_name)

    tmux new-window -n "${review_name}" "zsh -ic 'gm-pr-review ${pr_number}; zsh'"

    tmux rename-window "${review_name}"
    cl-pr-review-subagents "${pr_number}"
}

ai-pr-review() {
    local pr_number="$1"
    if [[ -z "$pr_number" ]]; then
        echo "Usage: ai-pr-review <PR番号>" >&2
        return 1
    fi

    local review_name
    review_name=$(_review_window_name)

    tmux new-window -n "${review_name}" "zsh -ic 'cl-pr-review-subagents ${pr_number}; zsh'"
    tmux new-window -n "${review_name}" "zsh -ic 'gm-pr-review ${pr_number}; zsh'"

    tmux rename-window "${review_name}"
    cl-pr-review "${pr_number}"
}
