#!/bin/bash

# Herdr の workspace をブランチ付きで一覧し、fzf で選んだ workspace へ移動する。
# --list は fzf を通さず候補行 (workspace_id<TAB>表示文字列) を出力する。
# 現在の workspace は末尾に置くため、開いて Enter で直前に使っていた側へ戻れる。

set -euo pipefail

herdr_bin="${HERDR_BIN_PATH:-herdr}"

# 剥ぎ取られた popup 環境は LANG を欠くことがあり、多バイトの label 表示が壊れる。
export LANG="${LANG:-en_US.UTF-8}"

function _picker_json() {
    local output
    output=$("$herdr_bin" "$@") || { echo "herdr $* failed" >&2; return 1; }
    if ! jq -e '.result | type == "object"' >/dev/null 2>&1 <<< "$output"; then
        echo "herdr $* returned invalid JSON" >&2
        return 1
    fi
    printf '%s\n' "$output"
}

function _picker_branch() {
    local dir="$1" branch
    [[ -n "$dir" && -d "$dir" ]] || return 0
    branch=$(git -C "$dir" branch --show-current 2>/dev/null) || return 0
    if [[ -z "$branch" ]]; then
        branch=$(git -C "$dir" rev-parse --short HEAD 2>/dev/null) || return 0
    fi
    printf '%s' "$branch"
}

function _picker_list() {
    local workspaces panes rows
    workspaces=$(_picker_json workspace list) || return 1
    panes=$(_picker_json pane list) || return 1

    # 各 workspace の active tab で focused な pane、無ければ先頭 pane の cwd を採る。
    # foreground_cwd は実行中プロセス (例: Claude の plugin cache) を指すことがあるので使わない。
    rows=$(jq -rn --argjson ws "$workspaces" --argjson ps "$panes" '
        ($ps.result.panes // []) as $panes
        | ($ws.result.workspaces // [])
        | (map(select(.focused | not)) + map(select(.focused)))[]
        | . as $w
        | ([$panes[] | select(.tab_id == $w.active_tab_id)]
           | (map(select(.focused)) + .) | first | .cwd // "") as $cwd
        | [$w.workspace_id, (if $w.focused then "1" else "0" end), ($w.label // $w.workspace_id), $cwd]
        | @tsv
    ') || { echo "failed to build workspace rows" >&2; return 1; }

    local id focused label cwd branch shown_cwd marker
    while IFS=$'\t' read -r id focused label cwd; do
        [[ -n "$id" ]] || continue
        branch=$(_picker_branch "$cwd")
        shown_cwd="$cwd"
        if [[ -n "$HOME" && ( "$cwd" == "$HOME" || "$cwd" == "$HOME/"* ) ]]; then
            shown_cwd="~${cwd#"$HOME"}"
        fi
        marker="  "
        [[ "$focused" == 1 ]] && marker="* "
        printf '%s\t%s%s' "$id" "$marker" "$label"
        [[ -n "$branch" ]] && printf '  \033[32m%s\033[0m' "$branch"
        [[ -n "$shown_cwd" ]] && printf '  \033[2m%s\033[0m' "$shown_cwd"
        printf '\n'
    done <<< "$rows"
}

if [[ "${1:-}" == --list ]]; then
    _picker_list
    exit
fi

rows=$(_picker_list)
[[ -n "$rows" ]] || { echo "no herdr workspaces found" >&2; exit 1; }

selected=$(fzf --ansi --delimiter $'\t' --with-nth 2.. --no-sort \
    --prompt 'workspace> ' <<< "$rows") || exit 130

"$herdr_bin" workspace focus "${selected%%$'\t'*}" >/dev/null
