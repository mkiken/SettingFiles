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
    pr_number=$(_fgh_select_pr_number)
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

# worktreeパスから "リポジトリ名/ブランチ末尾"（デフォルトブランチならリポジトリ名のみ）を計算して出力
# rename-window-git.sh の命名ロジックを流用（tmuxへの副作用なし）
_review_window_git_name() {
    local target="$1"
    (
        cd "$target" 2>/dev/null || exit 1
        local repo_root repo_name branch default_branch abbrev
        repo_root=$(git rev-parse --show-toplevel 2>/dev/null)
        if [[ -z "$repo_root" ]]; then
            print -r -- "$(basename "$target")"; exit 0
        fi
        repo_name=$(basename "$repo_root")
        branch=$(git branch --show-current 2>/dev/null)
        [[ -z "$branch" ]] && branch=$(git rev-parse --short HEAD 2>/dev/null)
        default_branch=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null)
        default_branch="${default_branch##refs/remotes/origin/}"
        if [[ -n "$default_branch" && "$branch" = "$default_branch" ]]; then
            print -r -- "$repo_name"; exit 0
        fi
        abbrev="${branch##*/}"
        (( ${#abbrev} > 20 )) && abbrev="${abbrev:0:20}…"
        print -r -- "${repo_name}/${abbrev}"
    )
}

# リポジトリ→worktreeの2段階選択後、reviewセッションに新windowを作りAIレビューを実行する共通ヘルパー
# 引数: 元関数名, [元関数に渡す追加引数...]
_fwmon-review() {
    local func_name="$1"; shift

    local worktree_path
    worktree_path=$(_filter_zoxide_workmux_worktree_path)
    if [[ $? -ne 0 ]] || [[ -z "$worktree_path" ]]; then
        return $EXIT_CODE_SIGINT
    fi

    local window_name
    window_name=$(_review_window_git_name "$worktree_path")
    [[ -z "$window_name" ]] && window_name="review"

    local review_command
    review_command=$(_ai_review_tmux_command "$func_name" "$@") || return 1

    if tmux has-session -t=review 2>/dev/null; then
        # 既存reviewセッションに移動せず新window追加
        tmux new-window -d -t review: -c "$worktree_path" \
            -n "$window_name" "zsh -ic ${(q)review_command}"
    else
        # reviewセッションを作成し、初期windowにレビューを載せる（空window回避）
        tmux new-session -d -s review -c "$worktree_path" \
            -n "$window_name" "zsh -ic ${(q)review_command}"
    fi
}

fwmon-review()           { _fwmon-review review "$@" }
fwmon-review-subagents() { _fwmon-review review-subagents "$@" }
fwmon-review-all()       { _fwmon-review review-all "$@" }
