#!/bin/bash
# Claude aliases - Common for bash and zsh

cl() {
    no_notify claude "$@"
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
    clo --allow-dangerously-skip-permissions "/my:pr-review $*"
}

cl-pr-review-subagents() {
    cl --allow-dangerously-skip-permissions "/pr-review-subagents $*"
}

_cl-pr-comment-review() {
    clo --allow-dangerously-skip-permissions "/my:pr-comment-review $*"
}

_cl-pr-comment-implement() {
    clp "/my:pr-comment-implement $*"
}

cl-pr-body() {
    clo --allow-dangerously-skip-permissions "/my:pr-body $*"
}

cl-pr-create() {
    local branch
    branch=$(br_fmt) || return $?
    clo "/pr-create-by-branch $branch"
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