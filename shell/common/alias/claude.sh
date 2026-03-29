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

cl-web-summary() {
    clo "/my:web-summary $*"
}

cl-pr-review() {
    clo --dangerously-skip-permissions "/my:pr-review $*"
}

cl-pr-review-subagents() {
    cl --dangerously-skip-permissions "/pr-review-subagents $*"
}

_cl-pr-comment-review() {
    clo --dangerously-skip-permissions "/my:pr-comment-review $*"
}

_cl-pr-comment-implement() {
    clp "/my:pr-comment-implement $*"
}

cl-pr-body() {
    clo --dangerously-skip-permissions "/my:pr-body $*"
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