#!/bin/bash

# Herdr の全 tab を所属 workspace 名・ブランチ付きで一覧し、fzf で選んだ tab へ移動する。
# --list は fzf を通さず候補行 (tab_id, TAB, 表示文字列) を出力する。
# 現在の workspace の tab は末尾に置くため、開いて Enter で直前に使っていた側へ戻れる。

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
    local workspaces tabs panes rows
    workspaces=$(_picker_json workspace list) || return 1
    tabs=$(_picker_json tab list) || return 1
    panes=$(_picker_json pane list) || return 1

    # workspace 順 (現在の workspace は末尾) × tab の number 順で tab 行だけを作る。
    # cwd は対象 tab で focused な pane、無ければ先頭 pane のものを採る。
    # foreground_cwd は実行中プロセス (例: Claude の plugin cache) を指すことがあるので使わない。
    rows=$(jq -rn --argjson ws "$workspaces" --argjson ts "$tabs" --argjson ps "$panes" '
        def strip: sub("^\\[[0-9]+\\] "; "");
        def cwd_of($tab_id):
            [($ps.result.panes // [])[] | select(.tab_id == $tab_id)]
            | (map(select(.focused)) + .) | first | .cwd // "";
        ($ts.result.tabs // []) as $tabs
        | ($ws.result.workspaces // [])
        | (map(select(.focused | not)) + map(select(.focused)))[]
        | . as $w
        | ($tabs | map(select(.workspace_id == $w.workspace_id)) | sort_by(.number)[]
           | [.tab_id, (if .focused then "1" else "0" end),
              ($w.label // $w.workspace_id | strip), (.label // .tab_id), cwd_of(.tab_id)])
        | join("\u001f")
    ') || { echo "failed to build picker rows" >&2; return 1; }

    local id focused ws_label label cwd branch shown_cwd marker
    # TAB は空白扱いで連続すると空フィールドが潰れ、cwd が空の行で後続の値がずれるため、
    # 空白でない区切り文字 (US) を使う。
    while IFS=$'\x1f' read -r id focused ws_label label cwd; do
        [[ -n "$id" ]] || continue
        branch=$(_picker_branch "$cwd")
        shown_cwd="$cwd"
        if [[ -n "$HOME" && ( "$cwd" == "$HOME" || "$cwd" == "$HOME/"* ) ]]; then
            shown_cwd="~${cwd#"$HOME"}"
        fi
        marker="  "
        [[ "$focused" == 1 ]] && marker="* "
        # fzf は隠しフィールドを検索できないため、workspace 名は表示文字列の先頭に置く。
        printf '%s\t%s\033[2m%s ›\033[0m %s' "$id" "$marker" "$ws_label" "$label"
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
[[ -n "$rows" ]] || { echo "no herdr tabs found" >&2; exit 1; }

selected=$(fzf --ansi --delimiter $'\t' --with-nth 2.. --no-sort --layout=reverse \
    --prompt 'tab> ' <<< "$rows") || exit 130

tab_id="${selected%%$'\t'*}"
# tab focus だけで別 workspace の tab へ移れるかは未検証なので、先に workspace へ移る。
"$herdr_bin" workspace focus "${tab_id%%:*}" >/dev/null
"$herdr_bin" tab focus "$tab_id" >/dev/null
