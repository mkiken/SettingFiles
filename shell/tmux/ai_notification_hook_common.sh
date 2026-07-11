#!/bin/bash
# AI通知shフック（claude/gemini/codex）の共通ヘッダ
# 契約: 呼び出し側フックは DEBUG_ENABLED / DEBUG_LOG / AI_HOOK_LABEL（例: Claude）を定義してから source する
# （debug_log は実行時に変数を参照するため source 後の定義でも動くが、契約として先に定義する）
# AI_HOOK_EMOJI_ID は未定義なら tmux_emoji.conf の EMOJI_ID_<LABEL大文字> から補完される
# Codexには ~/.codex/common が無いため、フック共有モジュールは shell/tmux/ に置く（CLAUDE.md参照）
# エラーハンドリング方針: 通知フックでは set -e を有効化しない（DEBUG時も含む）。
# bashの配列アクセス等で意図せず中断し、通知が届かなくなるため。

_AI_HOOK_SET_DIR="${SET:-$HOME/Desktop/repository/SettingFiles/}"

# notification関数を読み込み
source "${_AI_HOOK_SET_DIR}shell/zsh/alias/notification.zsh"
# This hook notifies intentionally; bypass the AI-session suppression inherited from the parent process.
export NOTIFY_FORCE=1
# 絵文字アイコン定義を読み込み
source "${_AI_HOOK_SET_DIR}shell/tmux/tmux_emoji.conf"
# tmuxウィンドウラベル取得関数を読み込み
source "${_AI_HOOK_SET_DIR}shell/tmux/tmux_window_info.sh"
# 通知タイトル生成・時間フォーマットヘルパー
source "${_AI_HOOK_SET_DIR}shell/tmux/tmux_notification_title.sh"
# tmuxウィンドウ名のアイコン操作（承認待ち/終了アイコンの先行設定用）
source "${_AI_HOOK_SET_DIR}shell/tmux/tmux_window_name.sh"
# 通知要約ヘルパー（セッション時間計算など）
source "${_AI_HOOK_SET_DIR}shell/tmux/ai_notification_summary.sh"

# デバッグ関数
debug_log() {
    if [[ "${DEBUG_ENABLED}" == "true" ]]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "${DEBUG_LOG}"
    fi
}

# AI_HOOK_LABEL から tmux_emoji.conf の EMOJI_ID_<LABEL大文字> を引く
_resolve_ai_hook_emoji_id() {
    local var_name
    var_name="EMOJI_ID_$(echo "$1" | tr '[:lower:]' '[:upper:]')"
    echo "${!var_name}"
}
if [[ -n "${AI_HOOK_LABEL:-}" && -z "${AI_HOOK_EMOJI_ID:-}" ]]; then
    AI_HOOK_EMOJI_ID="$(_resolve_ai_hook_emoji_id "${AI_HOOK_LABEL}")"
fi

# 通知グループ名用の小文字ラベル。呼び出し側フックが直接定義すればtr起動を省ける
if [[ -z "${AI_HOOK_LABEL_LOWER:-}" ]]; then
    AI_HOOK_LABEL_LOWER="$(echo "${AI_HOOK_LABEL:-}" | tr '[:upper:]' '[:lower:]')"
fi

# 通知タイトルを組み立て（例: build_ai_title "✅" "終了" → "✅ Claude終了 <ウィンドウ情報>"）
# Usage: build_ai_title <status_emoji> <title_suffix>
build_ai_title() {
    build_notification_title "$1" "${AI_HOOK_LABEL}$2" "${AI_HOOK_EMOJI_ID}"
}

# グループ通知用のグループ名を出力（例: claude-<session_id>）
# Usage: build_notification_group <session_id>
build_notification_group() {
    echo "${AI_HOOK_LABEL_LOWER}-$1"
}

# エラー時フォールバック通知（🤖 <AI>終了 タイトル + 呼び出し側の NOTIFICATION_SOUND）
# Usage: hook_fallback_notify <message>
hook_fallback_notify() {
    notify "$(build_ai_title "🤖" "終了")" "$1" "${NOTIFICATION_SOUND}"
}
