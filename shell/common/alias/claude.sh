#!/bin/bash
# Claude aliases - Common for bash and zsh

cl() {
    no_notify claude --allow-dangerously-skip-permissions "$@"
}

# `o` selects Opus.
clo() {
    cl --model 'opus' "$@"
}

# `s` selects Sonnet.
cls() {
    cl --model 'sonnet' "$@"
}

clsh() {
    cls --effort high "$@"
}

cloh() {
    clo --effort high "$@"
}

# `f` selects Fable.
clf() {
    cl --model 'fable' "$@"
}

clh() {
    clf --effort high "$@"
}

clhp() {
    clh --permission-mode plan "$@"
}

clp() {
    cl --permission-mode plan "$@"
}

clr() { cl --resume "$@"; }

cloh() { clo --effort high "$@"; }

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
    clh --dangerously-skip-permissions "/pr-review $pr_number${review_prompt:+ $review_prompt} ultrathink"
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
    clsh --dangerously-skip-permissions "/pr-review-subagents $pr_number${review_prompt:+ $review_prompt} ultrathink"
}

cl-review-merge() {
    local run_dir="$1"
    if [[ -z "$run_dir" ]]; then
        echo "Usage: cl-review-merge <run_dir>" >&2
        return 1
    fi
    cloh --dangerously-skip-permissions "/review-merge $run_dir"
}

cl-review-post() {
    clo --dangerously-skip-permissions "/review-post $*"
}

cl-review-fix() {
    clh "/review-fix $*"
}

_cl-pr-comment-review() {
    clo --effort high --dangerously-skip-permissions "/pr-comment-review $* ultrathink"
}

_cl-pr-comment-implement() {
    clp "/pr-comment-implement $*"
}

_clh-pr-comment-implement() {
    clhp "/pr-comment-implement $*"
}

cl-pr-body() {
    local pr_number
    pr_number=$(gh pr view --json number --jq .number) || {
        echo "現在のブランチに対応するPRが見つかりません。" >&2
        return 1
    }
    clo --dangerously-skip-permissions "/pr-body $pr_number $*"
}

# PR作成系のalias/skillから呼ぶレビュワー設定のリマインダ。
# レビュワーが設定済みかは判定せず常に出力する。本リポジトリのPR作成経路は
# いずれもレビュワーを設定しないため、判定しても常に未設定になる。
# 出力先はstderr。将来コマンド置換で呼ばれてもstdoutを汚さないため。
pr_reviewer_reminder() {
    echo "リマインド: PRのレビュワー設定を忘れないでください。" >&2
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
    local ai_exit
    clo --dangerously-skip-permissions "/pr-body $pr_number"
    ai_exit=$?
    pr_reviewer_reminder
    return $ai_exit
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
