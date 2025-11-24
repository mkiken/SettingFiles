#!/bin/zsh

alias update-gemini='npm update -g @google/gemini-cli'

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
    gmp "/pr-review $*"
}

gm-pr-body() {
    gmp "/pr-body $*"
}

gm-pr-comment-review() {
    gmp "/pr-comment-review $*"
}