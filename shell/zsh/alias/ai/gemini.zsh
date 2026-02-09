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

alias gm-pr-comment-review='noglob _gm-pr-comment-review'
_gm-pr-comment-review() {
    gmp -i "/pr-comment-review $*"
}

alias gm-pr-comment-implement='noglob _gm-pr-comment-implement'
_gm-pr-comment-implement() {
    gmp -i "/pr-comment-implement $*"
}

gm-web-summary() {
    gmp --allowed-tools "WebFetchTool" -i "/web-summary $*"
}