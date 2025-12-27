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
    clo "/my:pr-review $*"
}

cl-pr-comment-review() {
    clo "/my:pr-comment-review $*"
}

cl-pr-comment-implement() {
    clo "/my:pr-comment-implement $*"
}

cl-pr-body() {
    clo "/my:pr-body $*"
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