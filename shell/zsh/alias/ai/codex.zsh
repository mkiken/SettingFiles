#!/bin/zsh

_cx_homebrew_prefix() {
    if [[ -n "${BREW_PREFIX:-}" ]]; then
        print -r -- "$BREW_PREFIX"
    elif command -v brew >/dev/null 2>&1; then
        brew --prefix
    else
        print -r -- "/opt/homebrew"
    fi
}

# Project-local Node managers can put per-version global bins before Homebrew.
# Keep cx on the Homebrew Codex install so updates are not repo-specific.
cx-update() {
    local homebrew_prefix="$(_cx_homebrew_prefix)"
    local npm_bin="${homebrew_prefix}/bin/npm"
    if [[ ! -x "$npm_bin" ]]; then
        echo "cx-update: Homebrew npm not found: $npm_bin" >&2
        return 1
    fi

    PATH="${homebrew_prefix}/bin:$PATH" "$npm_bin" i -g @openai/codex@latest
}

cx() {
    local homebrew_prefix="$(_cx_homebrew_prefix)"
    local codex_bin="${homebrew_prefix}/bin/codex"
    if [[ ! -x "$codex_bin" ]]; then
        echo "cx: Homebrew codex not found: $codex_bin" >&2
        return 1
    fi

    # codex and npm use env node, so put Homebrew bin first for the command too.
    PATH="${homebrew_prefix}/bin:$PATH" no_notify "$codex_bin" "$@"
    local codex_status=$?

    if (( ${+functions[remove_tmux_window_icon]} )); then
        remove_tmux_window_icon true
    else
        echo "cx: remove_tmux_window_icon is not defined; tmux window icon was not cleaned up" >&2
    fi

    return $codex_status
}

cxh() {
    cx -c 'model_reasoning_effort="xhigh"' "$@"
}

cxr() { cx resume "$@" }

cxhr() { cxh resume "$@" }

cx-pr-body() {
    local pr_number
    pr_number=$(gh pr view --json number --jq .number) || {
        echo "現在のブランチに対応するPRが見つかりません。" >&2
        return 1
    }
    cx --dangerously-bypass-approvals-and-sandbox "\$pr-body PR #$pr_number のbodyを生成して $*"
}

cx-pr-create() {
    local title="$*"
    if [[ -z "$title" ]]; then
        echo 'Usage: cx-pr-create "<title>"' >&2
        return 1
    fi

    local branch
    branch=$(br_fmt) || return $?

    gh pr create --base "$branch" --title "$title" --body "" || return $?

    local pr_number
    pr_number=$(gh pr view --json number --jq .number) || {
        echo "作成したPR番号を取得できませんでした。" >&2
        return 1
    }
    cx --dangerously-bypass-approvals-and-sandbox "\$pr-body PR #$pr_number のbodyを生成して"
}

cx-pr-review() {
    local pr_number
    pr_number=$(gh pr view --json number --jq .number) || {
        echo "現在のブランチに対応するPRが見つかりません。" >&2
        return 1
    }
    cx -c 'model_reasoning_effort="xhigh"' --dangerously-bypass-approvals-and-sandbox "\$pr-review PR #$pr_number をレビューして $*"
}

cx-pr-review-subagent() {
    local pr_number
    pr_number=$(gh pr view --json number --jq .number) || {
        echo "現在のブランチに対応するPRが見つかりません。" >&2
        return 1
    }
    cx -c 'model_reasoning_effort="xhigh"' --dangerously-bypass-approvals-and-sandbox "\$pr-review-subagents PR #$pr_number をレビューして $*"
}

alias cx-pr-comment-review='noglob _cx-pr-comment-review'
alias cx-pcr='noglob _cx-pr-comment-review'
_cx-pr-comment-review() {
    cx -c 'model_reasoning_effort="xhigh"' --dangerously-bypass-approvals-and-sandbox "\$pr-comment-review $*"
}

alias cx-pr-comment-implement='noglob _cx-pr-comment-implement'
alias cx-pci='noglob _cx-pr-comment-implement'
_cx-pr-comment-implement() {
    cx -c 'model_reasoning_effort="xhigh"' "\$pr-comment-implement $*"
}
