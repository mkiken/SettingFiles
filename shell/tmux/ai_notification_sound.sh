#!/bin/bash
# AI通知の音名をイベント種別で一元管理する共有モジュール。
# 音はagent（claude/codex/gemini）ではなくイベント種別で決まる（全AI共通）。
# tmux経路の共通ヘッダ（ai_notification_hook_common.sh）とHerdrプラグイン
# （notify-on-agent-status.sh）の双方からsourceされる。
# Codexには ~/.codex/common が無いため、フック共有モジュールは shell/tmux/ に置く（CLAUDE.md参照）。
# zshrc初期化中にsourceされ得るファイル群と同様、exitは使わない（source-only）。
# 注: コンテキスト残量アラート音（Tink）は context-alert.zsh 側で別管理。ここには含めない。

# 通知音を返す（terminal-notifier -sound へ渡す音名）。
# Usage: ai_notification_sound <event>
#   completed → 完了（正常終了）
#   waiting   → 応答待ち・承認待ち
#   error     → エラー停止
#   その他/空 → default（システム既定音）
ai_notification_sound() {
    case "$1" in
        completed) echo 'Hero' ;;
        waiting)   echo 'Glass' ;;
        error)     echo 'Basso' ;;
        *)         echo 'default' ;;
    esac
}
