#!/usr/bin/env bash
# セッション内の全windowのAI状態を集約し、最高優先度のアイコンをuser optionに書き込む
# 引数: $1 = session_id (例: $0)
SESSION_ID="$1"
[ -z "$SESSION_ID" ] && exit 0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
source "$SCRIPT_DIR/tmux_emoji.conf"

WINDOWS=$(tmux list-windows -t "$SESSION_ID" -F "#W" 2>/dev/null) || exit 0

ICON=""
for emoji in "$EMOJI_STATUS_NOTIFICATION" "$EMOJI_STATUS_ONGOING" "$EMOJI_STATUS_COMPLETED"; do
    if printf '%s' "$WINDOWS" | grep -qF "$emoji"; then
        ICON="$emoji"
        break
    fi
done

KEY="@session_ai_status_${SESSION_ID#\$}"
if [ -n "$ICON" ]; then
    tmux set-option -gq "$KEY" "$ICON"
else
    tmux set-option -gqu "$KEY" 2>/dev/null || true
fi
