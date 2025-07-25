#!/bin/bash
# Claude aliases - Common for bash and zsh

cl() {
    claude --verbose "$@"
}

clo() {
    cl --model opus "$@"
}

cl-web-summary() {
    clo "/web-summary $*"
}

cl-pr-review() {
    clo "/pr-review $*"
}

cl-pr-body() {
    clo "/pr-body $*"
}

alias update-cc='npm i -g @anthropic-ai/claude-code'