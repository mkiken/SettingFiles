#!/bin/zsh
# Herdr event hook for `pane.agent_status_changed`: replaces Herdr's plain OS toast
# with this repository's rich Mac notification (terminal-notifier, session title,
# workspace/tab label, sound), matching the look of the Claude/Codex/Gemini hooks.
#
# Deliberately no `set -e`: a failed lookup should fall back to "no notification",
# never abort mid-way and leave the agent silently un-notified (same policy as
# ai/claude/hooks/stop-send-notification.sh).

REPO_ROOT="${SET:-$HOME/Desktop/repository/SettingFiles}"

# Herdr injects HERDR_PLUGIN_EVENT_JSON with the shape:
#   {"event":"pane_agent_status_changed","data":{"pane_id":...,"workspace_id":...,"agent_status":...,"agent":...}}
event_json="${HERDR_PLUGIN_EVENT_JSON:-}"
agent="$(print -r -- "$event_json" | jq -r '.data.agent // empty' 2>/dev/null)"
# `status` is a read-only zsh special parameter (last exit code) — use agent_status instead.
agent_status="$(print -r -- "$event_json" | jq -r '.data.agent_status // empty' 2>/dev/null)"

# Only completed (done) or awaiting input (blocked) are worth a notification.
# idle = already-seen completion, working/unknown = nothing to report yet.
case "$agent_status" in
  done|blocked) ;;
  *) exit 0 ;;
esac

herdr_bin="${HERDR_BIN_PATH:-herdr}"
pane_id="${HERDR_PANE_ID:-}"
[[ -z "$pane_id" ]] && exit 0

# Conversation title comes from `pane get` (not present in the event/context JSON).
pane_json="$("$herdr_bin" pane get "$pane_id" 2>/dev/null)"
[[ -z "$pane_json" ]] && exit 0

title_text="$(print -r -- "$pane_json" | jq -r '.result.pane.terminal_title_stripped // empty' 2>/dev/null)"
session_id="$(print -r -- "$pane_json" | jq -r '.result.pane.agent_session.value // empty' 2>/dev/null)"
[[ -z "$title_text" ]] && title_text="(no title)"

# Tab display number is already in HERDR_PLUGIN_CONTEXT_JSON as `.tab_label` — no extra call needed.
context_json="${HERDR_PLUGIN_CONTEXT_JSON:-}"
tab_label="$(print -r -- "$context_json" | jq -r '.tab_label // empty' 2>/dev/null)"

# Workspace display number isn't in the context JSON; resolve it with one `workspace list` call.
ws_id="${HERDR_WORKSPACE_ID:-}"
ws_number=""
if [[ -n "$ws_id" ]]; then
  ws_number="$("$herdr_bin" workspace list 2>/dev/null \
    | jq -r --arg w "$ws_id" '.result.workspaces[]? | select(.workspace_id==$w) | .number // empty' 2>/dev/null)"
fi

screen_label=""
if [[ -n "$ws_number" && -n "$tab_label" ]]; then
  screen_label=" 🖥️${ws_number}-${tab_label}"
fi

source "${REPO_ROOT}/shell/tmux/tmux_emoji.conf"

case "$agent" in
  claude) id_emoji="$EMOJI_ID_CLAUDE" ;;
  codex)  id_emoji="$EMOJI_ID_CODEX" ;;
  gemini) id_emoji="$EMOJI_ID_GEMINI" ;;
  *)      id_emoji="🤖" ;;
esac

case "$agent_status" in
  done)
    status_emoji="$EMOJI_STATUS_COMPLETED"
    label_text="完了"
    ;;
  blocked)
    status_emoji="$EMOJI_STATUS_NOTIFICATION"
    label_text="入力待ち"
    ;;
esac

agent_label="${agent:0:1:u}${agent:1}"
now="$(date '+%H:%M:%S')"
title="${id_emoji}${status_emoji} ${agent_label}${label_text}${screen_label} 🕰️${now}"

group=""
if [[ -n "$agent" && -n "$session_id" ]]; then
  group="${agent}-${session_id}"
fi

source "${REPO_ROOT}/shell/zsh/alias/notification.zsh"

# NOTIFY_NO_DECORATE: this pane is outside tmux, so notify()'s auto tmux-label
# decoration would be a no-op anyway, but it also strips our own time suffix —
# suppress it since we build the full title (including time) ourselves.
# NOTIFY_FORCE: bypass AI-session suppression; this hook intentionally notifies.
NOTIFY_NO_DECORATE=1 NOTIFY_FORCE=1 notify "$title" "$title_text" "Hero" "$group"
