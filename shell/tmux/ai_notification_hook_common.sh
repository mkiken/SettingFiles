#!/bin/bash
# AI通知shフック（claude/gemini/codex）の共通ヘッダ
# 契約: 呼び出し側フックは DEBUG_ENABLED / DEBUG_LOG を定義してから source する
# （debug_log は実行時に変数を参照するため source 後の定義でも動くが、契約として先に定義する）
# Codexには ~/.codex/common が無いため、フック共有モジュールは shell/tmux/ に置く（CLAUDE.md参照）

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

# デバッグ関数
debug_log() {
    if [[ "${DEBUG_ENABLED}" == "true" ]]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "${DEBUG_LOG}"
    fi
}
