#!/bin/zsh
# AI cross-tool aliases

# rename-window-git.sh を呼んで git ベースのウィンドウ名を計算し、🔍プレフィックス付きで返す
_review_window_name() {
    local set_dir="${SET:-$HOME/Desktop/repository/SettingFiles}"
    source "${set_dir}/shell/tmux/tmux_emoji.conf"
    "${set_dir}/shell/tmux/rename-window-git.sh"
    local git_name
    git_name=$(tmux display-message -p '#W')
    # 絵文字プレフィックスを除去してから 🔍 を付与（アイコンスタック防止）
    git_name=$(python3 "${set_dir}/shell/tmux/tmux_emoji.py" "${git_name}")
    echo "${EMOJI_STATUS_REVIEW}${git_name}"
}

review() {
    local pr_number
    pr_number=$(gh pr view --json number --jq .number) || {
        echo "現在のブランチに対応するPRが見つかりません。" >&2
        return 1
    }

    local review_name current_window
    current_window=$(tmux display-message -p '#{window_id}')
    review_name=$(_review_window_name)

    tmux new-window -n "${review_name}" "zsh -ic 'gm-pr-review; zsh'"

    tmux rename-window -t "${current_window}" "${review_name}"
    cl-pr-review
}

review-subagents() {
    local pr_number
    pr_number=$(gh pr view --json number --jq .number) || {
        echo "現在のブランチに対応するPRが見つかりません。" >&2
        return 1
    }

    local review_name current_window
    current_window=$(tmux display-message -p '#{window_id}')
    review_name=$(_review_window_name)

    tmux new-window -n "${review_name}" "zsh -ic 'gm-pr-review; zsh'"

    tmux rename-window -t "${current_window}" "${review_name}"
    cl-pr-review-subagents
}

review-all() {
    local pr_number
    pr_number=$(gh pr view --json number --jq .number) || {
        echo "現在のブランチに対応するPRが見つかりません。" >&2
        return 1
    }

    local review_name current_window
    current_window=$(tmux display-message -p '#{window_id}')
    review_name=$(_review_window_name)

    tmux new-window -n "${review_name}" "zsh -ic 'cl-pr-review-subagents; zsh'"
    tmux new-window -n "${review_name}" "zsh -ic 'gm-pr-review; zsh'"

    tmux rename-window -t "${current_window}" "${review_name}"
    cl-pr-review
}
