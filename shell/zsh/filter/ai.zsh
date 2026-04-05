#!/bin/zsh

# fzfでPRを選択し、checkoutしてからAIレビュー関数を実行する共通ヘルパー
# 引数: 元関数名, [元関数に渡す追加引数...]
_fai-pr-review() {
    local func_name="$1"
    shift

    # dirty check
    if ! git diff-index --quiet HEAD -- 2>/dev/null || [[ -n $(git ls-files --others --exclude-standard) ]]; then
        echo "作業中のファイルがあります。stashまたはcommitしてください。" >&2
        return 1
    fi

    # fzf PR選択
    local pr_number
    pr_number=$(ghpl | filter | awk '{print $1}')
    if [[ -z "$pr_number" ]]; then
        echo "PRが選択されませんでした。" >&2
        return 1
    fi

    # checkout
    gh co "$pr_number"

    # checkout後は元関数が現在ブランチからPR番号を自動取得する
    "$func_name" "$@"
}

fcl-pr-review()              { _fai-pr-review cl-pr-review "$@" }
fcl-pr-review-subagents()    { _fai-pr-review cl-pr-review-subagents "$@" }
fgm-pr-review()              { _fai-pr-review gm-pr-review "$@" }
freview()           { _fai-pr-review review "$@" }
freview-subagents() { _fai-pr-review review-subagents "$@" }
freview-all()       { _fai-pr-review review-all "$@" }

# worktreeをfilterで選択し、cdしてからAIレビュー関数を実行する共通ヘルパー
# 引数: 元関数名, [元関数に渡す追加引数...]
_fwmo-review() {
    local func_name="$1"; shift
    fwmo || return $?
    "$func_name" "$@"
}

fwmo-review()           { _fwmo-review review "$@" }
fwmo-review-subagents() { _fwmo-review review-subagents "$@" }
fwmo-review-all()       { _fwmo-review review-all "$@" }

# worktreeをfilterで選択し、新しいtmuxウィンドウでAIレビュー関数を実行する共通ヘルパー
# 引数: 元関数名, [元関数に渡す追加引数...]
_fwmon-review() {
    local func_name="$1"; shift
    local worktree_path
    worktree_path=$(_filter_workmux_worktree_path)
    if [[ $? -ne 0 ]] || [[ -z "$worktree_path" ]]; then
        return $EXIT_CODE_SIGINT
    fi
    tmux new-window -c "$worktree_path" "zsh -ic '${func_name}; zsh'"
}

fwmon-review()           { _fwmon-review review "$@" }
fwmon-review-subagents() { _fwmon-review review-subagents "$@" }
fwmon-review-all()       { _fwmon-review review-all "$@" }
