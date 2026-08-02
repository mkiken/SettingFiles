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

if [[ -n "${ZSH_VERSION:-}" ]]; then
    _HERDR_STATUS_ICON_DIR="$(builtin cd -q -- "$(/usr/bin/dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
else
    _HERDR_STATUS_ICON_DIR="$(builtin cd -- "$(/usr/bin/dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
fi
if [[ -z "${EMOJI_STATUS_NOTIFICATION:-}" ]]; then
    source "${_HERDR_STATUS_ICON_DIR}/tmux_emoji.conf"
fi

# シェル所有の入力待ち✋マーカーのTTL（秒）。プロンプト放置は正当なので長め(24h)に
# とり、シェルがマーカーを消せずに死んだ場合のスタック防止バックストップとする。
_HERDR_SHELL_STATUS_TTL=86400

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

# herdr-tab-labelが現在tabのHerdr既定本文を概要slugへ差し替える。手動本文は
# 変更せず、番号prefix、AI識別子、状態アイコン、context badgeは純粋関数側で
# 保持する。Herdr外はno-op、Herdr内の解決/rename失敗は呼び出し元へ返す。
set_herdr_task_tab_label() {
    local base_label="$1"
    [[ -z "${base_label}" ]] && return 1
    [[ -n "${TMUX:-}" ]] && return 0
    { [[ -n "${HERDR_ENV:-}" ]] || [[ -n "${HERDR_PANE_ID:-}" ]]; } || return 0
    command -v herdr >/dev/null 2>&1 || return 1

    local tab_id
    tab_id="$(_herdr_resolve_tab_id)"
    [[ -z "${tab_id}" ]] && return 1

    local current_label
    current_label="$(herdr tab get "${tab_id}" 2>/dev/null | jq -r '.result.tab.label // empty' 2>/dev/null)"
    [[ -z "${current_label}" ]] && return 1

    local new_label
    new_label="$(python3 "${_HERDR_STATUS_ICON_DIR}/tmux_window_name.py" compute-initial-task-label "${current_label}" "${base_label}" 2>/dev/null)"
    [[ -z "${new_label}" ]] && return 1
    [[ "${new_label}" == "${current_label}" ]] && return 0

    herdr tab rename "${tab_id}" "${new_label}" >/dev/null 2>&1
}

# 更新前promptを保持する稼働中セッション向け互換入口。
set_herdr_worktree_tab_label() {
    set_herdr_task_tab_label "$@"
}

# シェル所有✋マーカーのパスを返す。notify-richプラグインのラベル再構築が
# シェル設置の✋を潰さないよう、マーカー存在中はプラグイン側がグリフをピン留めする
# （ラベル文字列だけではシェル✋とプラグイン✋(agent blocked)を区別できないため、
# 帯域外の所有権シグナルとしてファイルを使う）。キー式はプラグインの
# managed_label_state_file と同じサニタイズ（socket + tab_id）。
_herdr_shell_status_marker_path() {
    local tab_id="$1"
    [[ -z "${tab_id}" ]] && return 1
    local session_key="${HERDR_SOCKET_PATH:-default}"
    session_key="${session_key//[^A-Za-z0-9._-]/_}"
    local tab_key="${tab_id//[^A-Za-z0-9._-]/_}"
    echo "${XDG_CACHE_HOME:-$HOME/.cache}/herdr-shell-status/${session_key}/${tab_key}"
}

# 有効なマーカー（TTL内・内容が✋）ならグリフをechoする。stale/不正内容は
# 削除して空を返す。全てfail-safe（呼び出し元を止めない）。
_herdr_shell_status_marker_read() {
    local marker_path
    marker_path="$(_herdr_shell_status_marker_path "$1")" || return 0
    [[ -f "${marker_path}" ]] || return 0
    local mtime now
    mtime="$(stat -f %m "${marker_path}" 2>/dev/null)"
    now="$(date +%s)"
    if [[ -z "${mtime}" ]] || (( now - mtime > _HERDR_SHELL_STATUS_TTL )); then
        rm -f "${marker_path}" 2>/dev/null
        return 0
    fi
    local glyph=""
    IFS= read -r glyph < "${marker_path}" 2>/dev/null
    if [[ "${glyph}" != "${EMOJI_STATUS_NOTIFICATION}" ]]; then
        rm -f "${marker_path}" 2>/dev/null
        return 0
    fi
    echo "${glyph}"
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

    # ✋はrename前にマーカーを書く（rename直後にプラグインが発火しても見えるように）。
    # ✋以外のグリフは待ち状態の終了を意味するのでマーカーを消す。
    local marker_path
    marker_path="$(_herdr_shell_status_marker_path "${tab_id}")"
    if [[ -n "${marker_path}" ]]; then
        if [[ "${status_emoji}" == "${EMOJI_STATUS_NOTIFICATION}" ]]; then
            mkdir -p "${marker_path%/*}" 2>/dev/null
            printf '%s\n' "${status_emoji}" > "${marker_path}" 2>/dev/null
        else
            rm -f "${marker_path}" 2>/dev/null
        fi
    fi

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

    # クリーンアップrenameの前にマーカーを消す（レース中のプラグインが消えかけの
    # マーカーで再ピンしないように）。プラグインが削除直前に読んでいた場合の残余
    # レースは、次のプラグインイベントで自己修復する。
    local marker_path
    marker_path="$(_herdr_shell_status_marker_path "${tab_id}")"
    [[ -n "${marker_path}" ]] && rm -f "${marker_path}" 2>/dev/null

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
