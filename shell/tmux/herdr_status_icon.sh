#!/bin/bash
# シェル状態アイコン（AI以外: 入力待ち✋・完了✅・失敗❌）をHerdrのtab/workspaceに
# 反映するヘルパー。tmux_window_name.sh の Herdr 版で、notify() から source される。
#
# tab（tmux windowに相当）: 後勝ちでラベルの状態アイコン部分を差し替える。
#   AI識別子（✴️/💎/🪷）は現ラベルから継承して保持する（tmux_window_name.pyの
#   compute-updated-label/compute-cleaned-labelサブコマンドを再利用）。
# workspace（tmux sessionに相当・spaces表示）: 同workspace内のシェル所有状態を
#   ✋>❌>✅の優先度でOR集約し、`herdr workspace report-metadata`の
#   shell_statusトークンに書く。AIが書くtabラベルの状態とは分離する。
#
# クリア契機は3つ: プロンプト応答（✋: _finish_prompt_wait_notification）、
# 次コマンド開始（✅/❌: _notification_preexec）、そしてタブfocus
# （✅/❌のみ: clear_herdr_shell_status_state。notify-richプラグインの
# pane.focusedイベントから呼ばれる。「見た＝確認済み」として落とす）。
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
_HERDR_SHELL_STATUS_STATE_TTL=86400

# herdr CLIの解決点を1箇所に集約する。notify-richプラグインはstripped PATH
# （/usr/bin:/bin:/usr/sbin:/sbin）で起動されHomebrewのherdrがPATH上に無いため、
# プラグイン経路から呼ばれる関数はbare `herdr`ではなくこれを使う。
_herdr_cli() {
    if [[ -n "${HERDR_BIN_PATH:-}" ]]; then
        "${HERDR_BIN_PATH}" "$@"
    else
        herdr "$@"
    fi
}

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

# シェル所有の✅/❌状態キャッシュ。✋はプラグイン側のpinにも使う既存markerを
# 所有権シグナルにするため別保存する。タブラベルではAI状態と区別できない。
_herdr_shell_status_state_path() {
    local tab_id="$1"
    [[ -z "${tab_id}" ]] && return 1
    local session_key="${HERDR_SOCKET_PATH:-default}"
    session_key="${session_key//[^A-Za-z0-9._-]/_}"
    local tab_key="${tab_id//[^A-Za-z0-9._-]/_}"
    echo "${XDG_CACHE_HOME:-$HOME/.cache}/herdr-shell-status-state/${session_key}/${tab_key}"
}

# このファイルは対話zshからもsourceされるため、rmはユーザーaliasへ展開され得る。
# cache entryは単一ファイルなので、alias非依存のunlinkでfail-safeに削除する。
_herdr_delete_cache_file() {
    local cache_file="$1"
    [[ -z "${cache_file}" ]] && return 0
    /bin/unlink "${cache_file}" 2>/dev/null || true
}

_herdr_shell_status_state_read() {
    local state_path
    state_path="$(_herdr_shell_status_state_path "$1")" || return 0
    [[ -f "${state_path}" ]] || return 0
    local mtime now
    mtime="$(stat -f %m "${state_path}" 2>/dev/null)"
    now="$(date +%s)"
    if [[ -z "${mtime}" ]] || (( now - mtime > _HERDR_SHELL_STATUS_STATE_TTL )); then
        _herdr_delete_cache_file "${state_path}"
        return 0
    fi
    local glyph=""
    IFS= read -r glyph < "${state_path}" 2>/dev/null
    case "${glyph}" in
        "${EMOJI_STATUS_COMPLETED}"|"${EMOJI_STATUS_ERROR}") echo "${glyph}" ;;
        *) _herdr_delete_cache_file "${state_path}" ;;
    esac
}

_herdr_shell_status_state_write() {
    local tab_id="$1"
    local glyph="$2"
    local state_path
    state_path="$(_herdr_shell_status_state_path "${tab_id}")" || return 0
    case "${glyph}" in
        "${EMOJI_STATUS_COMPLETED}"|"${EMOJI_STATUS_ERROR}")
            mkdir -p "${state_path%/*}" 2>/dev/null
            printf '%s\n' "${glyph}" > "${state_path}" 2>/dev/null
            ;;
        *) _herdr_delete_cache_file "${state_path}" ;;
    esac
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
        _herdr_delete_cache_file "${marker_path}"
        return 0
    fi
    local glyph=""
    IFS= read -r glyph < "${marker_path}" 2>/dev/null
    if [[ "${glyph}" != "${EMOJI_STATUS_NOTIFICATION}" ]]; then
        _herdr_delete_cache_file "${marker_path}"
        return 0
    fi
    echo "${glyph}"
}

# workspace内の全tabのシェル所有状態を ✋>❌>✅ の優先度でOR集約し、集約結果を返す。
# AIプラグインが書くtabラベルは読まない。該当なしは空文字。
_herdr_aggregate_workspace_status() {
    local workspace_id="$1"
    local tab_ids
    tab_ids="$(_herdr_cli tab list --workspace "${workspace_id}" 2>/dev/null | jq -r '.result.tabs[]?.tab_id // empty' 2>/dev/null)"
    [[ -z "${tab_ids}" ]] && return 0
    # ループ本体でlocalを宣言しない: zshのlocalはtypesetと同一で、既に宣言済みの
    # 変数を再宣言すると現在値をstdoutへ出力する（bashは無音）。この関数の出力は
    # コマンド置換で集約結果として読まれるため、宣言はループ外に置く。
    local emoji tab_id glyph
    for emoji in "${EMOJI_STATUS_NOTIFICATION}" "${EMOJI_STATUS_ERROR}" "${EMOJI_STATUS_COMPLETED}"; do
        while IFS= read -r tab_id; do
            [[ -z "${tab_id}" ]] && continue
            glyph="$(_herdr_shell_status_marker_read "${tab_id}")"
            [[ -z "${glyph}" ]] && glyph="$(_herdr_shell_status_state_read "${tab_id}")"
            if [[ "${glyph}" == "${emoji}" ]]; then
                echo "${emoji}"
                return 0
            fi
        done <<< "${tab_ids}"
    done
}

# workspaceトークンを再集約して反映する（想定グリフ1文字なら書き込み、それ以外はclear）
# 集約結果は書き込む前に検証する: 想定外の文字列をトークンに焼き付けると
# Spacesサイドバーにそのまま表示され、次の更新まで残り続けるため。
_herdr_refresh_workspace_token() {
    local workspace_id="$1"
    [[ -z "${workspace_id}" ]] && return 0
    local aggregated
    aggregated="$(_herdr_aggregate_workspace_status "${workspace_id}")"
    case "${aggregated}" in
        "${EMOJI_STATUS_NOTIFICATION}"|"${EMOJI_STATUS_ERROR}"|"${EMOJI_STATUS_COMPLETED}") ;;
        *) aggregated="" ;;
    esac
    if [[ -n "${aggregated}" ]]; then
        _herdr_cli workspace report-metadata "${workspace_id}" --source shell-status --token "shell_status=${aggregated}" >/dev/null 2>&1 || true
    else
        _herdr_cli workspace report-metadata "${workspace_id}" --source shell-status --clear-token shell_status >/dev/null 2>&1 || true
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

    # ✋はrename前にmarkerを書く。✅/❌は状態キャッシュへ保存する。
    # どちらも後段のworkspace集約はtabラベルでなくこの状態を読む。
    local marker_path
    marker_path="$(_herdr_shell_status_marker_path "${tab_id}")"
    if [[ -n "${marker_path}" ]]; then
        if [[ "${status_emoji}" == "${EMOJI_STATUS_NOTIFICATION}" ]]; then
            mkdir -p "${marker_path%/*}" 2>/dev/null
            printf '%s\n' "${status_emoji}" > "${marker_path}" 2>/dev/null
        else
            _herdr_delete_cache_file "${marker_path}"
        fi
    fi
    _herdr_shell_status_state_write "${tab_id}" "${status_emoji}"

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

# 指定tabのシェル所有✅/❌だけをクリアする（✋マーカーは触らない）。タブをfocus
# した＝完了/失敗を見たので確認済みとして落とす、という契機で呼ばれる。
# remove_herdr_status_iconとの違い:
#   - tab_id/workspace_idを引数で受ける（プラグインには呼び出し元シェルが無く、
#     HERDR_TAB_ID/HERDR_PANE_IDから解決できない）
#   - _herdr_status_availableを呼ばない（そのゲートのcommand -v herdrは
#     プラグインのstripped PATHでfalseになる。herdrは_herdr_cli経由で叩く）
#   - ✋マーカーを消さない。✋は「今まさにreadでブロック中」という生きた状態で、
#     focusしただけで消すと応答待ちを見落とす。マーカー生存中はラベルの状態
#     グリフもプラグインのピン留めに任せてrenameしない。
# Usage: clear_herdr_shell_status_state "w5G:t4" "w5G"
clear_herdr_shell_status_state() {
    local tab_id="$1"
    local workspace_id="$2"
    [[ -z "${tab_id}" ]] && return 0

    local state_path
    state_path="$(_herdr_shell_status_state_path "${tab_id}")" || return 0
    # focusイベントは頻繁に飛ぶ。状態キャッシュを作るのは
    # _herdr_shell_status_state_writeだけなので、不在＝シェルは✅/❌を持たない。
    # ここでstat 1回だけ払い、herdr/jq/python3の起動をすべて回避する。
    [[ -f "${state_path}" ]] || return 0

    _herdr_delete_cache_file "${state_path}"

    local marker_glyph
    marker_glyph="$(_herdr_shell_status_marker_read "${tab_id}")"
    if [[ -z "${marker_glyph}" ]]; then
        local current_label new_label
        current_label="$(_herdr_cli tab get "${tab_id}" 2>/dev/null | jq -r '.result.tab.label // empty' 2>/dev/null)"
        new_label="$(python3 "${_HERDR_STATUS_ICON_DIR}/tmux_window_name.py" compute-cleaned-label "${current_label}" 2>/dev/null)"
        if [[ -n "${new_label}" && "${new_label}" != "${current_label}" ]]; then
            _herdr_cli tab rename "${tab_id}" "${new_label}" >/dev/null 2>&1 || true
        fi
    fi

    [[ -n "${workspace_id}" ]] && _herdr_refresh_workspace_token "${workspace_id}"
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
    _herdr_delete_cache_file "${marker_path}"
    _herdr_shell_status_state_write "${tab_id}" ""

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
