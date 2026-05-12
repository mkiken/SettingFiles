#!/bin/zsh

alias cx-update='npm i -g @openai/codex@latest'

cx() {
    no_notify codex "$@"
}

cxr() { cx resume "$@" }

cx-pr-body() {
    local pr_number
    pr_number=$(gh pr view --json number --jq .number) || {
        echo "現在のブランチに対応するPRが見つかりません。" >&2
        return 1
    }
    cx --dangerously-bypass-approvals-and-sandbox "\$pr-body PR #$pr_number のbodyを生成して $*"
}

cx-pr-create() {
    local branch
    branch=$(br_fmt) || return $?
    cx "\$pr-create-by-branch $branch に向けてPRを作成して"
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
