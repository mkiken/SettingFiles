#!/bin/zsh

alias update-gm='npm update -g @google/gemini-cli'

gm() {
    no_notify gemini "$@"
}

gmf() {
    gm --model flash "$@"
}

gmp() {
    gm --model pro "$@"
}

gm-pr-review() {
    gmp -i "/pr-review $*"
}

gm-pr-body() {
    gmp -i "/pr-body $*"
}

gm-pr-comment-review() {
    gmp -i "/pr-comment-review $*"
}

gm-web-summary() {
    gmp --allowed-tools "WebFetchTool" -i "/web-summary $*"
}