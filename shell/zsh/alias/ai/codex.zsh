#!/bin/zsh

alias cx-update='npm i -g @openai/codex@latest'

cx() {
    no_notify codex "$@"
}

cx-pr-review() {
    local pr_number
    pr_number=$(gh pr view --json number --jq .number) || {
        echo "現在のブランチに対応するPRが見つかりません。" >&2
        return 1
    }
    cx "pr-review スキルを使って PR #$pr_number をレビュー $*"
}
