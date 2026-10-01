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
        codex_args=(--model gpt-6-sol "$@")
    fi

    no_notify homebrew_run codex "${codex_args[@]}"
    codex_status=$?

    return $codex_status
}

cxeh() {
    cx -c 'model_reasoning_effort="high"' "$@"
}

# `s` selects Sol.
cxs() {
    cx --model gpt-6-sol "$@"
}

# `a` selects Astra.
cxa() {
    cx --model gpt-6-astra "$@"
}

# `t` selects Terra.
cxt() {
    cx --model gpt-5.6-terra "$@"
}

cxteh() {
    cxt -c 'model_reasoning_effort="high"'  "$@"
}

# `l` selects Luna.
cxl() {
    cx --model gpt-6-luna "$@"
}

cxmx() {
    cxa -c 'model_reasoning_effort="high"' "$@"
}

cxr() { cx resume "$@" }

cxmxr() { cxmx resume "$@" }

cx-pr-body() {
    local pr_number
    pr_number=$(gh pr view --json number --jq .number) || {
        echo "現在のブランチに対応するPRが見つかりません。" >&2
        return 1
    }
    cxteh --dangerously-bypass-approvals-and-sandbox "\$pr-body PR #$pr_number のbodyを生成して $*"
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
    local ai_exit
    cxmx --dangerously-bypass-approvals-and-sandbox "\$pr-body PR #$pr_number のbodyを生成して"
    ai_exit=$?
    pr_reviewer_reminder
    return $ai_exit
}

cx-pr-review() {
    local pr_number review_prompt
    _ai_pr_review_resolve_args pr_number review_prompt "$@" || return 1
    cxmx --dangerously-bypass-approvals-and-sandbox "\$pr-review PR #$pr_number をレビューして${review_prompt:+ $review_prompt}"
}

cx-pr-review-subagent() {
    local pr_number review_prompt
    _ai_pr_review_resolve_args pr_number review_prompt "$@" || return 1
    cxmx --dangerously-bypass-approvals-and-sandbox "\$pr-review-subagents PR #$pr_number をレビューして${review_prompt:+ $review_prompt}"
}

cx-review-merge() {
    local run_dir="$1"
    if [[ -z "$run_dir" ]]; then
        echo "Usage: cx-review-merge <run_dir>" >&2
        return 1
    fi
    cxmx --dangerously-bypass-approvals-and-sandbox "\$review-merge $run_dir"
}

cx-review-post() {
    cxmx --dangerously-bypass-approvals-and-sandbox "\$review-post $*"
}

cx-review-fix() {
    cxmx "\$review-fix $*"
}

alias cx-pr-comment-review='noglob _cx-pr-comment-review'
alias cx-pcr='noglob _cx-pr-comment-review'
_cx-pr-comment-review() {
    cxmx --dangerously-bypass-approvals-and-sandbox "\$pr-comment-review $*"
}

alias cx-pr-comment-implement='noglob _cx-pr-comment-implement'
alias cx-pci='noglob _cx-pr-comment-implement'
_cx-pr-comment-implement() {
    cxteh "\$pr-comment-implement $*"
}

alias cxmx-pr-comment-implement='noglob _cxmx-pr-comment-implement'
alias cxmx-pci='noglob _cxmx-pr-comment-implement'
_cxmx-pr-comment-implement() {
    cxmx "\$pr-comment-implement $*"
}
