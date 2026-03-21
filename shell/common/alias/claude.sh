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
    clo "/my:pr-review --allow-dangerously-skip-permissions $*"
}

cl-pr-review-subagents() {
    cl "/pr-review-subagents --allow-dangerously-skip-permissions $*"
}

_cl-pr-comment-review() {
    clo "/my:pr-comment-review --allow-dangerously-skip-permissions $*"
}

_cl-pr-comment-implement() {
    clp "/my:pr-comment-implement $*"
}

cl-pr-body() {
    clo "/my:pr-body $*"
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

alias update-cc='npm update -g @anthropic-ai/claude-code'