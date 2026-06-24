#!/bin/zsh

alias cx-update='npm i -g @openai/codex@latest'

cx() {
    no_notify codex "$@"
    local codex_status=$?

    if (( ${+functions[remove_tmux_window_icon]} )); then
        remove_tmux_window_icon true
    else
        echo "cx: remove_tmux_window_icon is not defined; tmux window icon was not cleaned up" >&2
    fi

    return $codex_status
}

cxh() {
    cx -c 'model_reasoning_effort="xhigh"' "$@"
}

cxr() { cx resume "$@" }

cxhr() { cxh resume "$@" }

cx-pr-body() {
    local pr_number
    pr_number=$(gh pr view --json number --jq .number) || {
        echo "現在のブランチに対応するPRが見つかりません。" >&2
        return 1
    }
    cx --dangerously-bypass-approvals-and-sandbox "\$pr-body PR #$pr_number のbodyを生成して $*"
}

cx-pr-create() {
    local title="$*"
    if [[ -z "$title" ]]; then
        echo 'Usage: cx-pr-create "<title>"' >&2
        return 1
    fi

    local branch
    branch=$(br_fmt) || return $?

    gh pr create --base "$branch" --title "$title" --body "" || return $?

    local pr_number
    pr_number=$(gh pr view --json number --jq .number) || {
        echo "作成したPR番号を取得できませんでした。" >&2
        return 1
    }
    cx --dangerously-bypass-approvals-and-sandbox "\$pr-body PR #$pr_number のbodyを生成して"
}

cx-pr-review() {
    local pr_number
    pr_number=$(gh pr view --json number --jq .number) || {
        echo "現在のブランチに対応するPRが見つかりません。" >&2
        return 1
    }
    cx -c 'model_reasoning_effort="xhigh"' --dangerously-bypass-approvals-and-sandbox "\$pr-review PR #$pr_number をレビューして $*"
}

cx-pr-review-subagent() {
    local pr_number
    pr_number=$(gh pr view --json number --jq .number) || {
        echo "現在のブランチに対応するPRが見つかりません。" >&2
        return 1
    }
    cx -c 'model_reasoning_effort="xhigh"' --dangerously-bypass-approvals-and-sandbox "\$pr-review-subagents PR #$pr_number をレビューして $*"
}

alias cx-pr-comment-review='noglob _cx-pr-comment-review'
alias cx-pcr='noglob _cx-pr-comment-review'
_cx-pr-comment-review() {
    cx -c 'model_reasoning_effort="xhigh"' --dangerously-bypass-approvals-and-sandbox "\$pr-comment-review $*"
}

alias cx-pr-comment-implement='noglob _cx-pr-comment-implement'
alias cx-pci='noglob _cx-pr-comment-implement'
_cx-pr-comment-implement() {
    cx -c 'model_reasoning_effort="xhigh"' "\$pr-comment-implement $*"
}
