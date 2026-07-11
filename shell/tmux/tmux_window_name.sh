#!/bin/bash
# tmuxウィンドウ名の絵文字プレフィックス操作ヘルパー
# 実装本体は tmux_window_name.py（AIフックと共通）。ここはCLI呼び出しの薄いラッパー。
# Usage: source this file, then call update_tmux_window_name "✋",
# add_tmux_context_alert_badge, remove_tmux_context_alert_badge, or remove_tmux_window_icon

_TMUX_WINDOW_NAME_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
# EMOJI_* 変数は呼び出し側（notify等）が参照するため引き続き公開する
# ai_notification_hook_common.sh 経由では読み込み済みのため二重sourceを避ける
if [[ -z "${EMOJI_ID_CLAUDE:-}" ]]; then
    source "${_TMUX_WINDOW_NAME_DIR}/tmux_emoji.conf"
fi

# tmuxセッション内かどうかを判定してpane_idを返す
# VSCode等からTMUX_PANEが継承されるケースを除外するためTERM_PROGRAM==tmuxも確認
# tmux外でpython3を起動しないためのホットパス用ガードとしても使う
_get_tmux_pane_id_for_window_name() {
    [[ -z "${TMUX_PANE}" || "${TERM_PROGRAM:-}" != "tmux" ]] && return 1
    echo "${TMUX_PANE}"
}

# 指定した絵文字ステータスをtmuxウィンドウ名のプレフィックスに設定する
# 第2引数でAI識別絵文字（EMOJI_ID_*）を状態アイコンの前に付けられる
# Usage: update_tmux_window_name "✋" ["✴️"]
update_tmux_window_name() {
    _get_tmux_pane_id_for_window_name >/dev/null || return 0
    python3 "${_TMUX_WINDOW_NAME_DIR}/tmux_window_name.py" update "$1" "${2:-}" 2>/dev/null || true
}

# context逼迫バッジを状態アイコンとは独立して追加する
add_tmux_context_alert_badge() {
    _get_tmux_pane_id_for_window_name >/dev/null || return 0
    python3 "${_TMUX_WINDOW_NAME_DIR}/tmux_window_name.py" add-badge 2>/dev/null || true
}

# context逼迫バッジだけを外し、AI状態アイコンは残す（バッジ不在時は1を返す）
remove_tmux_context_alert_badge() {
    _get_tmux_pane_id_for_window_name >/dev/null || return 0
    python3 "${_TMUX_WINDOW_NAME_DIR}/tmux_window_name.py" remove-badge 2>/dev/null
}

# tmuxウィンドウ名から絵文字プレフィックスを除去して元の名前に戻す
# 終了コード契約（0=成功/1=対象なし/2〜6=失敗理由）とreport_error時のstderr文言は
# tmux_window_name.py の remove サブコマンドが提供する
remove_tmux_window_icon() {
    if [[ "${1:-false}" == "true" ]]; then
        python3 "${_TMUX_WINDOW_NAME_DIR}/tmux_window_name.py" remove --report-error
    else
        python3 "${_TMUX_WINDOW_NAME_DIR}/tmux_window_name.py" remove 2>/dev/null
    fi
}
