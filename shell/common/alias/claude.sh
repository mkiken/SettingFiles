#!/bin/bash
# Claude aliases - Common for bash and zsh

cl() {
    no_notify claude --allow-dangerously-skip-permissions "$@"
}

clo() {
    cl --model opus "$@"
}

clp() {
    cl --permission-mode plan "$@"
}

clr() { cl --resume "$@" }

cl-web-summary() {
    clo "/my:web-summary $*"
}

cl-pr-review() {
    local pr_number
    pr_number=$(gh pr view --json number --jq .number) || {
        echo "現在のブランチに対応するPRが見つかりません。" >&2
        return 1
    }
    clo --effort max --dangerously-skip-permissions "/my:pr-review $pr_number $* ultrathink"
}

cl-pr-review-subagents() {
    local pr_number
    pr_number=$(gh pr view --json number --jq .number) || {
        echo "現在のブランチに対応するPRが見つかりません。" >&2
        return 1
    }
    clo --effort max --dangerously-skip-permissions "/pr-review-subagents $pr_number $* ultrathink"
}

_cl-pr-comment-review() {
    clo --effort max --dangerously-skip-permissions "/my:pr-comment-review $* ultrathink"
}

_cl-pr-comment-implement() {
    clp "/my:pr-comment-implement $*"
}

cl-pr-body() {
    local pr_number
    pr_number=$(gh pr view --json number --jq .number) || {
        echo "現在のブランチに対応するPRが見つかりません。" >&2
        return 1
    }
    clo --dangerously-skip-permissions "/my:pr-body $pr_number $*"
}

cl-pr-create() {
    local branch
    branch=$(br_fmt) || return $?
    clp "/pr-create-by-branch $branch"
}

cclog() {
     claude-code-log "$@"
}

cclogt() {
     cclog --tui "$@"
}

cclogb() {
     cclog --open-browser "$@"
}

alias cl-update='claude update'