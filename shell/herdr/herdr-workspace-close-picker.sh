#!/bin/bash

# Herdr の workspace を fzf で複数選び、確認のうえ一括で閉じる。
# 現在の workspace は一覧の末尾に置き、popup の親を巻き込まないよう必ず最後に閉じる。
# --list は fzf を通さず候補行 (workspace_id, TAB, 表示文字列) を出力する。

set -euo pipefail

herdr_bin="${HERDR_BIN_PATH:-herdr}"

# 剥ぎ取られた popup 環境は LANG を欠くことがあり、多バイトの label 表示が壊れる。
export LANG="${LANG:-en_US.UTF-8}"

function _close_json() {
    local output
    output=$("$herdr_bin" "$@") || { echo "herdr $* failed" >&2; return 1; }
    if ! jq -e '.result | type == "object"' >/dev/null 2>&1 <<< "$output"; then
        echo "herdr $* returned invalid JSON" >&2
        return 1
    fi
    printf '%s\n' "$output"
}

function _close_list() {
    local workspaces panes rows
    workspaces=$(_close_json workspace list) || return 1
    panes=$(_close_json pane list) || return 1

    # cwd は active tab で focused な pane、無ければ先頭 pane のものを採る。
    rows=$(jq -rn --argjson ws "$workspaces" --argjson ps "$panes" '
        def cwd_of($tab_id):
            [($ps.result.panes // [])[] | select(.tab_id == $tab_id)]
            | (map(select(.focused)) + .) | first | .cwd // "";
        ($ws.result.workspaces // [])
        | (map(select(.focused | not)) + map(select(.focused)))[]
        | [.workspace_id, (if .focused then "* " else "  " end) + (.label // .workspace_id),
           cwd_of(.active_tab_id)]
        | join("\u001f")
    ') || { echo "failed to build picker rows" >&2; return 1; }

    local id label cwd branch
    while IFS=$'\x1f' read -r id label cwd; do
        [[ -n "$id" ]] || continue
        printf '%s\t%s' "$id" "$label"
        if [[ -n "$cwd" && -d "$cwd" ]]; then
            branch=$(git -C "$cwd" branch --show-current 2>/dev/null || true)
            [[ -n "$branch" ]] && printf '  %s' "$branch"
            printf '  %s' "${cwd/#$HOME/~}"
        fi
        printf '\n'
    done <<< "$rows"
}

if [[ "${1:-}" == --list ]]; then
    _close_list
    exit
fi

rows=$(_close_list)
[[ -n "$rows" ]] || { echo "no herdr workspaces found" >&2; exit 1; }

selected=$(fzf --multi --delimiter $'\t' --with-nth 2.. --no-sort --layout=reverse \
    --prompt 'close workspace> ' --header 'Tab: 選択/解除 (複数可)  Enter: 確定  Esc: 中止  * は現在のworkspace' <<< "$rows") || exit 130
[[ -n "$selected" ]] || exit 130

# fzf の出力は選択順なので、一覧順 (現在の workspace が末尾) に並べ直す。
ordered=""
while IFS= read -r row; do
    if grep -qxF -- "$row" <<< "$selected"; then
        ordered+="$row"$'\n'
    fi
done <<< "$rows"

printf 'close %s workspace(s):\n' "$(grep -c . <<< "$ordered")"
sed 's/^[^\t]*\t/  /' <<< "$ordered"
printf '閉じる? y: 実行 / それ以外: 中止 [y/N] '
read -r -n1 answer || answer=""
printf '\n'
[[ "$answer" == [yY] ]] || exit 130

failed=0
while IFS=$'\t' read -r id _; do
    [[ -n "$id" ]] || continue
    if ! "$herdr_bin" workspace close "$id" >/dev/null; then
        echo "failed to close $id" >&2
        failed=1
    fi
done <<< "$ordered"
exit "$failed"
