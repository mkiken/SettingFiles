#!/bin/zsh
# Claude aliases - Load from common file

# Load common Claude aliases
source "${0:h}/../../../common/alias/claude.sh"

# PR comment commands need noglob for URLs with # fragments
alias cl-pr-comment-review='noglob _cl-pr-comment-review'
alias cl-pr-comment-implement='noglob _cl-pr-comment-implement'
alias clh-pr-comment-implement='noglob _clh-pr-comment-implement'
alias cl-pcr='noglob _cl-pr-comment-review'
alias cl-pci='noglob _cl-pr-comment-implement'
alias clh-pci='noglob _clh-pr-comment-implement'
