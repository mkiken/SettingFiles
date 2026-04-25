#!/bin/zsh

alias gm-update='brew upgrade gemini-cli'

gm() {
    no_notify gemini "$@"
}

gmr() { gm "/resume" "$@" }

gmf() {
    gm --model flash "$@"
}

gmp() {
    gm --model pro "$@"
}

gmfp() {
    gmf --approval-mode plan "$@"
}

gmpp() {
    gmp --approval-mode plan "$@"
}

gm-pr-review() {
    local pr_number
    pr_number=$(gh pr view --json number --jq .number) || {
        echo "現在のブランチに対応するPRが見つかりません。" >&2
        return 1
    }
    gmp --approval-mode yolo -i "/pr-review $pr_number $*"
}

gm-pr-body() {
    gmp -i "/pr-body $*"
}

alias gm-pr-comment-review='noglob _gm-pr-comment-review'
_gm-pr-comment-review() {
    gmp --approval-mode yolo -i "/pr-comment-review $*"
}

alias gm-pr-comment-implement='noglob _gm-pr-comment-implement'
_gm-pr-comment-implement() {
    gmp -i "/pr-comment-implement $*"
}

gm-web-summary() {
    gmp --allowed-tools "WebFetchTool" -i "/web-summary $*"
}