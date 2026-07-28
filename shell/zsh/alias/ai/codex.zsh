#!/bin/zsh

# Project-local Node managers can put per-version global bins before Homebrew.
# Keep cx on the Homebrew Codex install so updates are not repo-specific.
cx-update() {
    homebrew_npm i -g @openai/codex@latest
}

cx() {
    setopt localoptions localtraps
    # When codex dies to mashed Ctrl-C, zsh aborts this function too; the
    # always block still runs, and ignoring INT keeps further Ctrl-C from
    # killing the cleanup itself.
    local codex_status=130
    local -a codex_args
    if (( ${argv[(I)--model]} || ${argv[(I)--model=*]} || ${argv[(I)-m]} )); then
        codex_args=("$@")
    else
        codex_args=(--model gpt-5.6-terra "$@")
    fi

    {
        no_notify homebrew_run codex "${codex_args[@]}"
        codex_status=$?
    } always {
        trap '' INT
        if (( ${+functions[remove_tmux_window_icon]} )); then
            remove_tmux_window_icon true
        else
            echo "cx: remove_tmux_window_icon is not defined; tmux window icon was not cleaned up" >&2
        fi
    }

    return $codex_status
}

cxs() {
    cx --model gpt-5.6-sol "$@"
}

cxt() {
    cx --model gpt-5.6-terra "$@"
}

cxl() {
    cx --model gpt-5.6-luna "$@"
}

cxh() {
    cxs -c 'model_reasoning_effort="high"' "$@"
}

cxr() { cx resume "$@" }

cxhr() { cxh resume "$@" }

cx-pr-body() {
    local pr_number
    pr_number=$(gh pr view --json number --jq .number) || {
        echo "現在のブランチに対応するPRが見つかりません。" >&2
        return 1
    }
    cxh --dangerously-bypass-approvals-and-sandbox "\$pr-body PR #$pr_number のbodyを生成して $*"
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
    cxh --dangerously-bypass-approvals-and-sandbox "\$pr-body PR #$pr_number のbodyを生成して"
}

cx-pr-review() {
    local pr_number review_prompt
    _ai_pr_review_resolve_args pr_number review_prompt "$@" || return 1
    cxh --dangerously-bypass-approvals-and-sandbox "\$pr-review PR #$pr_number をレビューして${review_prompt:+ $review_prompt}"
}

cx-pr-review-subagent() {
    local pr_number review_prompt
    _ai_pr_review_resolve_args pr_number review_prompt "$@" || return 1
    cxh --dangerously-bypass-approvals-and-sandbox "\$pr-review-subagents PR #$pr_number をレビューして${review_prompt:+ $review_prompt}"
}

cx-review-merge() {
    local run_dir="$1"
    if [[ -z "$run_dir" ]]; then
        echo "Usage: cx-review-merge <run_dir>" >&2
        return 1
    fi
    cxh --dangerously-bypass-approvals-and-sandbox "\$review-merge $run_dir"
}

cx-review-post() {
    cxh --dangerously-bypass-approvals-and-sandbox "\$review-post $*"
}

cx-review-fix() {
    cxh "\$review-fix $*"
}

alias cx-pr-comment-review='noglob _cx-pr-comment-review'
alias cx-pcr='noglob _cx-pr-comment-review'
_cx-pr-comment-review() {
    cxh --dangerously-bypass-approvals-and-sandbox "\$pr-comment-review $*"
}

alias cx-pr-comment-implement='noglob _cx-pr-comment-implement'
alias cx-pci='noglob _cx-pr-comment-implement'
_cx-pr-comment-implement() {
    cx "\$pr-comment-implement $*"
}

alias cxh-pr-comment-implement='noglob _cxh-pr-comment-implement'
alias cxh-pci='noglob _cxh-pr-comment-implement'
_cxh-pr-comment-implement() {
    cxh "\$pr-comment-implement $*"
}
