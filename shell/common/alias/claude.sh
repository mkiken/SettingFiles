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
    clp "/my:web-summary $*"
}

cl-pr-review() {
    clp "/my:pr-review $*"
}

_cl-pr-comment-review() {
    clp "/my:pr-comment-review $*"
}

_cl-pr-comment-implement() {
    clp "/my:pr-comment-implement $*"
}

cl-pr-body() {
    clp "/my:pr-body $*"
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