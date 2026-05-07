#!/usr/bin/env bash
# セッション内の全windowのAI状態を集約し、最高優先度のアイコンをuser optionに書き込む
# 引数: $1 = session_id の数値部分（$は除去済み、例: 0）
SESSION_ID="$1"
[ -z "$SESSION_ID" ] && exit 0

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
source "$SCRIPT_DIR/tmux_emoji.conf"

# tmuxのtarget構文では$付きsession_idが必須（数値だけだとsession index扱いで失敗）
TMUX_TARGET="\$$SESSION_ID"

WINDOWS=$(tmux list-windows -t "$TMUX_TARGET" -F "#W" 2>/dev/null) || exit 0

ICON=""
for emoji in "$EMOJI_STATUS_NOTIFICATION" "$EMOJI_STATUS_ONGOING" "$EMOJI_STATUS_COMPLETED"; do
    if printf '%s' "$WINDOWS" | grep -qF "$emoji"; then
        ICON="$emoji"
        break
    fi
done

if [ -n "$ICON" ]; then
    tmux set-option -t "$TMUX_TARGET" -q "@session_ai_status" "$ICON"
else
    tmux set-option -t "$TMUX_TARGET" -qu "@session_ai_status" 2>/dev/null || true
fi
