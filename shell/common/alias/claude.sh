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
    clo "/web-summary $*"
}

cl-pr-review() {
    clo "/pr-review $*"
}

cl-pr-comment-review() {
    clo "/pr-comment-review $*"
}

cl-pr-comment-implement() {
    clo "/pr-comment-implement $*"
}

cl-pr-body() {
    clo "/pr-body $*"
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