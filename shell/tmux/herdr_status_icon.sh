#!/bin/bash
# シェル状態アイコン（AI以外: 入力待ち✋・完了✅・失敗❌）をHerdrのtab/workspaceに
# 反映するヘルパー。tmux_window_name.sh の Herdr 版で、notify() から source される。
#
# tab（tmux windowに相当）: 後勝ちでラベルの状態アイコン部分を差し替える。
#   AI識別子（✴️/💎/🪷）は現ラベルから継承して保持する（tmux_window_name.pyの
#   compute-updated-label/compute-cleaned-labelサブコマンドを再利用）。
# workspace（tmux sessionに相当・spaces表示）: 同workspace内の全tabラベルを
#   ✋>❌>🤖>✅の優先度でOR集約し、`herdr workspace report-metadata`の
#   shell_statusトークンに書く（tmuxの@session_ai_status user optionと等価）。
#
# 失敗はすべてfail-safe（no set -e）: 通知/アイコン付与に失敗しても呼び出し元の
# 処理を止めない（notify-on-agent-status.shと同じポリシー）。

_HERDR_STATUS_ICON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
if [[ -z "${EMOJI_STATUS_NOTIFICATION:-}" ]]; then
    source "${_HERDR_STATUS_ICON_DIR}/tmux_emoji.conf"
fi

# Herdr環境かつtmux外かどうかを判定する（tmux/Herdrは排他）
_herdr_status_available() {
    [[ -n "${NOTIFY_SILENT:-}" ]] && return 1
    [[ -n "${TMUX:-}" ]] && return 1
    { [[ -n "${HERDR_ENV:-}" ]] || [[ -n "${HERDR_PANE_ID:-}" ]]; } || return 1
    command -v herdr >/dev/null 2>&1
}

# tab_id/workspace_idを解決する。環境変数があれば優先し、無ければ`pane get`で解決
_herdr_resolve_tab_id() {
    if [[ -n "${HERDR_TAB_ID:-}" ]]; then
        echo "${HERDR_TAB_ID}"
        return 0
    fi
    [[ -z "${HERDR_PANE_ID:-}" ]] && return 1
    herdr pane get "${HERDR_PANE_ID}" 2>/dev/null | jq -r '.result.pane.tab_id // empty' 2>/dev/null
}

_herdr_resolve_workspace_id() {
    if [[ -n "${HERDR_WORKSPACE_ID:-}" ]]; then
        echo "${HERDR_WORKSPACE_ID}"
        return 0
    fi
    [[ -z "${HERDR_PANE_ID:-}" ]] && return 1
    herdr pane get "${HERDR_PANE_ID}" 2>/dev/null | jq -r '.result.pane.workspace_id // empty' 2>/dev/null
}

# workspace内の全tabラベルを ✋>❌>🤖>✅ の優先度でOR集約し、集約結果の絵文字を返す
# （tmuxのupdate-session-ai-status.shと同じOR集約方式）。該当なしは空文字。
_herdr_aggregate_workspace_status() {
    local workspace_id="$1"
    local labels
    labels="$(herdr tab list --workspace "${workspace_id}" 2>/dev/null | jq -r '.result.tabs[]?.label // empty' 2>/dev/null)"
    [[ -z "${labels}" ]] && return 0
    local emoji
    for emoji in "${EMOJI_STATUS_NOTIFICATION}" "${EMOJI_STATUS_ERROR}" "${EMOJI_STATUS_ONGOING}" "${EMOJI_STATUS_COMPLETED}"; do
        if printf '%s' "${labels}" | grep -qF "${emoji}"; then
            echo "${emoji}"
            return 0
        fi
    done
}

# workspaceトークンを再集約して反映する（非空なら書き込み、空ならclear）
_herdr_refresh_workspace_token() {
    local workspace_id="$1"
    [[ -z "${workspace_id}" ]] && return 0
    local aggregated
    aggregated="$(_herdr_aggregate_workspace_status "${workspace_id}")"
    if [[ -n "${aggregated}" ]]; then
        herdr workspace report-metadata "${workspace_id}" --source shell-status --token "shell_status=${aggregated}" >/dev/null 2>&1 || true
    else
        herdr workspace report-metadata "${workspace_id}" --source shell-status --clear-token shell_status >/dev/null 2>&1 || true
    fi
}

# 指定した状態アイコンをHerdrのtabラベル先頭に設定し、workspaceトークンも更新する
# AI識別子は現ラベルから継承して保持する（後勝ちで状態部分だけ差し替え）。
# Usage: update_herdr_status_icon "✋"
update_herdr_status_icon() {
    local status_emoji="$1"
    _herdr_status_available || return 0

    local tab_id
    tab_id="$(_herdr_resolve_tab_id)"
    [[ -z "${tab_id}" ]] && return 0

    local current_label
    current_label="$(herdr tab get "${tab_id}" 2>/dev/null | jq -r '.result.tab.label // empty' 2>/dev/null)"

    local new_label
    new_label="$(python3 "${_HERDR_STATUS_ICON_DIR}/tmux_window_name.py" compute-updated-label "${current_label}" "${status_emoji}" 2>/dev/null)"
    [[ -z "${new_label}" ]] && return 0

    if [[ "${new_label}" != "${current_label}" ]]; then
        herdr tab rename "${tab_id}" "${new_label}" >/dev/null 2>&1 || true
    fi

    local workspace_id
    workspace_id="$(_herdr_resolve_workspace_id)"
    _herdr_refresh_workspace_token "${workspace_id}"
    return 0
}

# Herdrのtabラベルから状態アイコンだけを除去する（AI識別子・バッジは残す）。
# workspaceトークンも再集約する。
remove_herdr_status_icon() {
    _herdr_status_available || return 0

    local tab_id
    tab_id="$(_herdr_resolve_tab_id)"
    [[ -z "${tab_id}" ]] && return 0

    local current_label
    current_label="$(herdr tab get "${tab_id}" 2>/dev/null | jq -r '.result.tab.label // empty' 2>/dev/null)"

    local new_label
    new_label="$(python3 "${_HERDR_STATUS_ICON_DIR}/tmux_window_name.py" compute-cleaned-label "${current_label}" 2>/dev/null)"

    if [[ -n "${new_label}" && "${new_label}" != "${current_label}" ]]; then
        herdr tab rename "${tab_id}" "${new_label}" >/dev/null 2>&1 || true
    fi

    local workspace_id
    workspace_id="$(_herdr_resolve_workspace_id)"
    _herdr_refresh_workspace_token "${workspace_id}"
    return 0
}
