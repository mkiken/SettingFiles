#!/bin/bash
# Claude aliases - Common for bash and zsh

cl() {
    no_notify claude --allow-dangerously-skip-permissions "$@"
}

clo() {
    cl --model 'opus[1m]' "$@"
}

clhm() {
    clfm --effort high "$@"
}

cls() {
    cl --model 'sonnet' "$@"
}

clf() {
    cl --model 'fable' "$@"
}

clfm() {
    clf --effort max "$@"
}

clp() {
    cl --permission-mode plan "$@"
}

clpm() {
    cl --permission-mode plan --effort max "$@"
}

clr() { cl --resume "$@"; }

clor() { clo --resume "$@"; }

clfr() { clf --resume "$@"; }

cl-web-summary() {
    clo "/web-summary $*"
}

cl-pr-review() {
    local pr_number review_prompt
    if [[ $# -gt 0 && "$1" =~ ^(#?[0-9]+|https?://[^[:space:]]+/pull/[0-9]+([/?#].*)?)$ ]]; then
        pr_number="${1#\#}"
        shift
    else
        pr_number=$(gh pr view --json number --jq .number) || {
            echo "現在のブランチに対応するPRが見つかりません。" >&2
            return 1
        }
    fi

    review_prompt="$*"
    clf --effort xhigh --dangerously-skip-permissions "/pr-review $pr_number${review_prompt:+ $review_prompt} ultrathink"
}

cl-pr-review-subagents() {
    local pr_number review_prompt
    if [[ $# -gt 0 && "$1" =~ ^(#?[0-9]+|https?://[^[:space:]]+/pull/[0-9]+([/?#].*)?)$ ]]; then
        pr_number="${1#\#}"
        shift
    else
        pr_number=$(gh pr view --json number --jq .number) || {
            echo "現在のブランチに対応するPRが見つかりません。" >&2
            return 1
        }
    fi

    review_prompt="$*"
    clf --effort xhigh --dangerously-skip-permissions "/pr-review-subagents $pr_number${review_prompt:+ $review_prompt} ultrathink"
}

cl-review-merge() {
    local run_dir="$1"
    if [[ -z "$run_dir" ]]; then
        echo "Usage: cl-review-merge <run_dir>" >&2
        return 1
    fi
    clf --effort high --dangerously-skip-permissions "/review-merge $run_dir"
}

cl-review-post() {
    clo --dangerously-skip-permissions "/review-post $*"
}

cl-review-fix() {
    clf --effort high "/review-fix $*"
}

_cl-pr-comment-review() {
    clo --effort high --dangerously-skip-permissions "/pr-comment-review $* ultrathink"
}

_cl-pr-comment-implement() {
    clp "/pr-comment-implement $*"
}

_clh-pr-comment-implement() {
    clp --effort high "/pr-comment-implement $*"
}

cl-pr-body() {
    local pr_number
    pr_number=$(gh pr view --json number --jq .number) || {
        echo "現在のブランチに対応するPRが見つかりません。" >&2
        return 1
    }
    clo --dangerously-skip-permissions "/pr-body $pr_number $*"
}

cl-pr-create() {
    local title="$*"
    if [[ -z "$title" ]]; then
        echo 'Usage: cl-pr-create "<title>"' >&2
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
    clo --dangerously-skip-permissions "/pr-body $pr_number"
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
