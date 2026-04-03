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

    # 元関数にPR番号と残りの引数を渡す
    "$func_name" "$pr_number" "$@"
}

fcl-pr-review()              { _fai-pr-review cl-pr-review "$@" }
fcl-pr-review-subagents()    { _fai-pr-review cl-pr-review-subagents "$@" }
fgm-pr-review()              { _fai-pr-review gm-pr-review "$@" }
fcl-gm-pr-review()           { _fai-pr-review cl-gm-pr-review "$@" }
fcl-gm-pr-review-subagents() { _fai-pr-review cl-gm-pr-review-subagents "$@" }
fai-pr-review()              { _fai-pr-review ai-pr-review "$@" }
