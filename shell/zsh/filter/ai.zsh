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

# Herdr popupはコマンド終了と同時に閉じるため、エラーメッセージが読めないまま消える。
# popup実行時のみキー入力を待って、原因を読み切れるようにする。
# 通常シェルからの直接実行やテストでは待たない（HERDR_POPUP_WRAPPEDが空）。
# HERDR_POPUP_COMMAND（p10k gate専用）ではなくHERDR_POPUP_WRAPPED（herdr-popup-run.shの
# pause契約変数）を見る。1変数に2つの意味を持たせると将来別箇所の判定が全popupへ波及するため分離している
_freview_pause_if_popup() {
    [[ -z "${HERDR_POPUP_WRAPPED:-}" ]] && return 0
    echo "エラーで終了しました。何かキーを押すと閉じます" >&2
    # 共通ラッパー(herdr-popup-run.sh)へpause済みを通知し二重待ちを防ぐ
    [[ -n "${HERDR_POPUP_PAUSE_MARK:-}" ]] && print -r -- "ai.zsh" >> "${HERDR_POPUP_PAUSE_MARK}" 2>/dev/null
    # ttyが無ければ待てないので読み取りは省く（待つと閉じられないpopupになる）。
    # 直前のメッセージはpause判定の観測点でもあるため、読み取りの可否に関わらず出す
    [[ -t 0 ]] || return 0
    local _discard
    read -k 1 -r _discard
    echo "" >&2
}

# 選択worktreeがレビュー可能な状態か確認する（親シェルからgit -Cで検査）。
# 追跡ファイルの変更はレビュー対象の差分に未コミット分が混入しうるため無条件で中断する。
# 未追跡ファイルだけならレビュー自体は成立するので、内容を見せたうえで続行可否を選ばせる
# （過去のAIレビューが残した一時ファイルでPR選択に到達できなくなるのを避けるため）
# 引数: worktree_path
_freview_confirm_clean_enough() {
    local worktree_path="$1"

    if ! git -C "$worktree_path" diff-index --quiet HEAD -- 2>/dev/null; then
        echo "${worktree_path} に作業中のファイルがあります。stashまたはcommitしてください。" >&2
        return 1
    fi

    local -a untracked
    untracked=("${(@f)$(git -C "$worktree_path" ls-files --others --exclude-standard)}")
    # コマンド置換が空文字を返すと1要素の空配列になるため、空要素を落として実数にする
    untracked=("${(@)untracked:#}")
    (( ${#untracked} == 0 )) && return 0

    echo "${worktree_path} に未追跡ファイルが ${#untracked} 件あります:" >&2
    # 大量の未追跡ファイルでpopupが埋まらないよう表示は先頭10件に抑える
    local -i shown=0
    local file
    for file in "${untracked[@]}"; do
        (( shown >= 10 )) && break
        echo "  ${file}" >&2
        shown+=1
    done
    (( ${#untracked} > shown )) && echo "  ... 他 $(( ${#untracked} - shown )) 件" >&2

    confirm "未追跡ファイルを残したままレビューを続行しますか？" --default-no --no-notify --single-key
}

# リポジトリ→worktree→PRを選択し、選択worktreeでcheckoutしてAIレビューを起動する
# 現ペインはcdしない。Herdr専用: reviewが作るworkspace(review-<worktree名>)を唯一の
# 新規workspaceにするため中継ペインを置かず、AI_REVIEW_CWDで対象worktreeをreviewへ伝える
# （コマンド前置のためexportされず、並列実行中の他プロセスへは漏れない）
# 引数: 元関数名, [元関数に渡す追加引数...]
_freview_worktree() {
    local func_name="$1"; shift

    if [[ "$(_ai_multiplexer_kind)" != "herdr" ]]; then
        echo "worktree選択付きレビューはHerdr内で実行してください（現在地でレビューするには -c）" >&2
        return 1
    fi

    # _review_run は [--no-merge] [pr] [prompt...] の順を前提とするため、
    # PR番号を自前で解決してここへ挿入するにはこの時点で--no-mergeを剥がして
    # 先に確保しておく必要がある（そのまま末尾に流すとPR番号の後ろに来て
    # PR参照と誤認されずAIプロンプトへ混入し、無効化される）
    local -a no_merge_flag=()
    if [[ "${1:-}" == "--no-merge" ]]; then
        no_merge_flag=(--no-merge)
        shift
    fi

    local worktree_path
    worktree_path=$(_filter_zoxide_git_worktree_path --label-prefix "$func_name")
    if [[ $? -ne 0 ]] || [[ -z "$worktree_path" ]]; then
        return $EXIT_CODE_SIGINT
    fi

    _freview_confirm_clean_enough "$worktree_path" || return 1

    # gh pr list はcwd依存のため、選択worktreeへcdしたサブシェルでPRを選ぶ
    # fzfはTUIを/dev/ttyに描くのでコマンド置換内でも動く
    # （_filter_zoxide_git_worktree_path が cdq + filter で同じことをしている）
    # --label-prefixにfunc_name（review/review-subagents）を渡し、fzfのpromptで
    # どのバリアントを実行中か常に見分けられるようにする
    local pr_number
    pr_number=$(cdq "$worktree_path" && _fgh_select_pr_number --label-prefix "$func_name")
    if [[ $? -ne 0 ]] || [[ -z "$pr_number" ]]; then
        return $EXIT_CODE_SIGINT
    fi

    # checkoutも選択worktree側で行う。失敗をこの場で覚知させるためreviewより前に実行する
    ( cdq "$worktree_path" && gh co "$pr_number" ) || {
        echo "gh co ${pr_number} に失敗しました: ${worktree_path}" >&2
        return 1
    }

    # freviewのシェル自体はcdしない（現ペインは元のリポジトリのまま）ため、
    # reviewが「現在のブランチから自動解決」を試みても選択worktreeとは無関係になる。
    # そのためPR番号は明示的に渡す（_fai-pr-review の自動解決前提は使えない）
    AI_REVIEW_CWD="$worktree_path" "$func_name" "${no_merge_flag[@]}" "$pr_number" "$@"
}

# -c 指定時のみ従来動作（現在地でPR選択→gh co→レビュー）
# -c は先頭のみ認識し、以降の引数はreviewへそのまま渡す（--no-merge/プロンプトと競合させない）
# エラー終了時のpopup pauseはここへ集約する。個別のエラー箇所に散らさないことで
# 将来増えるエラー経路も自動的に可視化される
# 引数: 元関数名, [-c] [元関数に渡す追加引数...]
_freview_dispatch() {
    local func_name="$1"; shift

    local dispatch_exit
    if [[ "${1:-}" == "-c" ]]; then
        shift
        _fai-pr-review "$func_name" "$@"
        dispatch_exit=$?
    else
        _freview_worktree "$func_name" "$@"
        dispatch_exit=$?
    fi

    # ピッカーのキャンセルは正常操作なので待たせない
    if (( dispatch_exit != 0 )) && (( dispatch_exit != EXIT_CODE_SIGINT )); then
        _freview_pause_if_popup
    fi
    return $dispatch_exit
}

freview()           { _freview_dispatch review "$@" }
freview-subagents() { _freview_dispatch review-subagents "$@" }

# 現在リポジトリのworktreeをfilterで選択し、cdしてからAIレビュー関数を実行する共通ヘルパー
# 引数: 元関数名, [元関数に渡す追加引数...]
_fwmo-review() {
    local func_name="$1"; shift
    fgwt || return $?
    "$func_name" "$@"
}

fwmo-review()           { _fwmo-review review "$@" }
fwmo-review-subagents() { _fwmo-review review-subagents "$@" }

# worktreeパスから "リポジトリ名/ブランチ末尾"（デフォルトブランチならリポジトリ名のみ）を計算して出力
# rename-window-git.sh の命名ロジックを流用（tmuxへの副作用なし）
# コマンド置換で呼ばれるため、cdはchpwdフック（_chpwd_ls_abbrevのpwd+ls出力）が
# 混入しないよう-qで抑制し、-qを解さないzoxideのcd関数上書きをbuiltinで回避する
_review_window_git_name() {
    local target="$1"
    (
        builtin cd -q "$target" 2>/dev/null || exit 1
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

# リポジトリ→worktreeの2段階選択後、reviewセッションに新windowを作りAIレビューを実行する（tmux版）
# 引数: 元関数名, [元関数に渡す追加引数...]
_fwmon_review_tmux() {
    local func_name="$1"; shift

    local worktree_path
    worktree_path=$(_filter_zoxide_git_worktree_path)
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

# リポジトリ→worktreeの2段階選択後、新規Herdr workspaceを作りその中でAIレビューを実行する（Herdr版）
# tmuxのnamed session "review" のような名前指定はHerdrにはできないため、都度新規workspaceを作る
# 引数: 元関数名, [元関数に渡す追加引数...]
_fwmon_review_herdr() {
    local func_name="$1"; shift

    local worktree_path
    worktree_path=$(_filter_zoxide_git_worktree_path)
    if [[ $? -ne 0 ]] || [[ -z "$worktree_path" ]]; then
        return $EXIT_CODE_SIGINT
    fi

    local window_name
    window_name=$(_review_window_git_name "$worktree_path")
    [[ -z "$window_name" ]] && window_name="review"

    local review_command
    review_command=$(_ai_review_command "$func_name" "$@") || return 1

    local ws_json
    ws_json=$(herdr workspace create --label review --cwd "$worktree_path" --no-focus) || {
        echo "herdr workspace createに失敗しました" >&2
        return 1
    }

    local ws_id
    ws_id=$(print -r -- "$ws_json" | jq -r '.result.workspace.workspace_id')
    if [[ -z "$ws_id" || "$ws_id" == "null" ]]; then
        echo "herdr workspace createの結果からworkspace_idを取得できませんでした" >&2
        return 1
    fi

    # 新規workspaceの初期tabのpaneでレビューを実行する
    local pane_id
    pane_id=$(print -r -- "$ws_json" | jq -r '.result.root_pane.pane_id')
    if [[ -z "$pane_id" || "$pane_id" == "null" ]]; then
        echo "herdr workspace createの結果からpane_idを取得できませんでした" >&2
        return 1
    fi

    herdr pane run "$pane_id" "$review_command" || {
        echo "herdr pane runに失敗しました (pane_id=${pane_id})" >&2
        return 1
    }
}

# 指定worktreeで新規Herdr workspaceを作り、そこへフォーカス移動する（frw -s のHerdr版）
# tmuxのswitch-clientで新セッションへ連れて行く挙動を尊重し--focusを明示する
# コマンド実行は不要（--cwdで新paneが目的ディレクトリで開くため、pane runは省略）
# 引数: cwd（作成するworkspaceの初期ディレクトリ）
_herdr_open_worktree_workspace() {
    local cwd="$1"
    local herdr_bin="${HERDR_BIN_PATH:-herdr}"

    local ws_json
    ws_json=$("$herdr_bin" workspace create --label "${cwd:t}" --cwd "$cwd" --focus) || {
        echo "herdr workspace createに失敗しました" >&2
        return 1
    }

    local ws_id
    ws_id=$(print -r -- "$ws_json" | jq -r '.result.workspace.workspace_id')
    if [[ -z "$ws_id" || "$ws_id" == "null" ]]; then
        echo "herdr workspace createの結果からworkspace_idを取得できませんでした" >&2
        return 1
    fi
}

# 指定worktreeで新規Herdr tabを作り、そこへフォーカス移動する（frw -w のHerdr版）
# tmuxのnew-window（-cのみ、フォーカスは新windowへ移る）挙動を尊重し--focusを明示する
# コマンド実行は不要（--cwdで新paneが目的ディレクトリで開くため、pane runは省略）
# 引数: cwd（作成するtabの初期ディレクトリ）
_herdr_open_worktree_tab() {
    local cwd="$1"
    local herdr_bin="${HERDR_BIN_PATH:-herdr}"

    local tab_json
    tab_json=$("$herdr_bin" tab create --cwd "$cwd" --label "${cwd:t}" --focus) || {
        echo "herdr tab createに失敗しました" >&2
        return 1
    }

    local pane_id
    pane_id=$(print -r -- "$tab_json" | jq -r '.result.root_pane.pane_id')
    if [[ -z "$pane_id" || "$pane_id" == "null" ]]; then
        echo "herdr tab createの結果からpane_idを取得できませんでした" >&2
        return 1
    fi
}

_herdr_open_worktree_split() {
    local cwd="$1"
    local direction="$2"
    local source_pane_id="${HERDR_ACTIVE_PANE_ID:-}"
    local herdr_bin="${HERDR_BIN_PATH:-herdr}"

    case "$direction" in
        down|right) ;;
        *)
            echo "Herdr split方向が不正です: $direction" >&2
            return 2
            ;;
    esac

    if [[ -z "$source_pane_id" ]]; then
        echo "Herdr popupの発火元paneを取得できませんでした" >&2
        return 1
    fi

    "$herdr_bin" pane split --pane "$source_pane_id" --direction "$direction" --cwd "$cwd" --focus || {
        echo "herdr pane splitに失敗しました" >&2
        return 1
    }
}

# リポジトリ→worktreeの2段階選択後、reviewセッション相当の場所に新windowを作りAIレビューを実行する
# 引数: 元関数名, [元関数に渡す追加引数...]
_fwmon-review() {
    case "$(_ai_multiplexer_kind)" in
        herdr) _fwmon_review_herdr "$@" ;;
        tmux) _fwmon_review_tmux "$@" ;;
        *)
            echo "tmuxまたはHerdr内で実行してください" >&2
            return 1
            ;;
    esac
}

fwmon-review()           { _fwmon-review review "$@" }
fwmon-review-subagents() { _fwmon-review review-subagents "$@" }
