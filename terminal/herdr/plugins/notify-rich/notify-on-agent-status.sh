#!/bin/zsh
# Herdr event hook for `pane.agent_status_changed`: replaces Herdr's plain OS toast
# with this repository's rich Mac notification (terminal-notifier, session title,
# workspace/tab label, sound), matching the look of the Claude/Codex hooks.
# Gemini is excluded entirely (see the agent=="gemini" guard below) and handled by
# its own hooks instead.
#
# Deliberately no `set -e`: a failed lookup should fall back to "no notification",
# never abort mid-way and leave the agent silently un-notified (same policy as
# ai/claude/hooks/stop-send-notification.sh).

REPO_ROOT="${SET:-$HOME/Desktop/repository/SettingFiles}"

# Herdrは[[events]]フックを[[keys.command]]と同じstripped PATH（Homebrewなし）で
# 起動するため、Homebrew専用のterminal-notifierが解決できず通知だけが失敗する
# （herdrはHERDR_BIN_PATH注入、jq/python3はシステム版で偶然動く）。先頭でなく
# 末尾に追加し、テストのfake_binや通常シェルのPATH優先順位は変えない。
case ":$PATH:" in
  *:/opt/homebrew/bin:*) ;;
  *) export PATH="$PATH:/opt/homebrew/bin:/usr/local/bin" ;;
esac

# Herdr injects HERDR_PLUGIN_EVENT_JSON with the shape:
#   {"event":"pane_agent_status_changed","data":{"pane_id":...,"workspace_id":...,"agent_status":...,"agent":...}}
event_json="${HERDR_PLUGIN_EVENT_JSON:-}"
agent="$(print -r -- "$event_json" | jq -r '.data.agent // empty' 2>/dev/null)"
# `status` is a read-only zsh special parameter (last exit code) — use agent_status instead.
agent_status="$(print -r -- "$event_json" | jq -r '.data.agent_status // empty' 2>/dev/null)"

# Gemini has no official Herdr installer integration, so its agent_status is derived
# solely from Herdr's screen-manifest detection and oscillates done<->working<->idle,
# firing this plugin many times per response (tab renames included). Gemini therefore
# opts OUT of the notify-rich single-source model entirely (notification AND tab
# rename) and notifies via its own AfterAgent/Notification tmux hooks
# (ai/gemini/hooks/notification.sh, HERDR guard relaxed there). Claude/Codex report
# status accurately via their installers and stay managed by this plugin.
[[ "$agent" == "gemini" ]] && exit 0

herdr_bin="${HERDR_BIN_PATH:-herdr}"
pane_id="${HERDR_PANE_ID:-}"
[[ -z "$pane_id" ]] && exit 0

# Conversation title comes from `pane get` (not present in the event/context JSON).
# タブアイコン処理（デフォルト数字ラベルの概要差し替え）と通知本文の両方で使うため
# ここで一度だけ取得する。
pane_json="$("$herdr_bin" pane get "$pane_id" 2>/dev/null)"
[[ -z "$pane_json" ]] && exit 0

source "${REPO_ROOT}/shell/tmux/tmux_emoji.conf"

case "$agent" in
  claude) id_emoji="$EMOJI_ID_CLAUDE" ;;
  codex)  id_emoji="$EMOJI_ID_CODEX" ;;
  gemini) id_emoji="$EMOJI_ID_GEMINI" ;;
  *)      id_emoji="🤖" ;;
esac

title_text="$(print -r -- "$pane_json" | jq -r '.result.pane.terminal_title_stripped // empty' 2>/dev/null)"
session_id="$(print -r -- "$pane_json" | jq -r '.result.pane.agent_session.value // empty' 2>/dev/null)"
[[ -z "$title_text" ]] && title_text="(no title)"

# タブ名先頭にAI識別子+状態アイコンを付与する（tmuxのwindow名アイコンと同じ思想）。
# working=進行中🤖 blocked=入力待ち✋ done=完了✅、idle(既読)/unknown(AI未検出)は
# アイコンを外して元のラベルに戻す。集約状態は `tab get` の agent_status（タブ内
# 複数paneがあってもHerdrが1つに集約済み）を使い、識別子だけ発火paneのagentを使う。
tab_id="$(print -r -- "$pane_json" | jq -r '.result.pane.tab_id // empty' 2>/dev/null)"
if [[ -n "$tab_id" ]]; then
  tab_json="$("$herdr_bin" tab get "$tab_id" 2>/dev/null)"
  if [[ -n "$tab_json" ]]; then
    tab_status="$(print -r -- "$tab_json" | jq -r '.result.tab.agent_status // empty' 2>/dev/null)"
    current_label="$(print -r -- "$tab_json" | jq -r '.result.tab.label // empty' 2>/dev/null)"
    tab_number="$(print -r -- "$tab_json" | jq -r '.result.tab.number // empty' 2>/dev/null)"

    status_emoji=""
    case "$tab_status" in
      working) status_emoji="$EMOJI_STATUS_ONGOING" ;;
      blocked) status_emoji="$EMOJI_STATUS_NOTIFICATION" ;;
      done)    status_emoji="$EMOJI_STATUS_COMPLETED" ;;
    esac

    base_label="$(python3 "${REPO_ROOT}/shell/tmux/tmux_emoji.py" "$current_label")"
    # herdrが自動採番/自動命名しただけのタブ（連番数字、または「Claude Code」等の
    # 既知agent自動命名ラベル）は、そのラベルよりMac通知と同じ会話概要を出す方が
    # 「どのタブか」を判別しやすい（20文字で切り詰め）。ユーザーが手動で付けた
    # 名前は温存する。判定は tmux_window_name.py の is-herdr-default-label に一元化。
    if python3 "${REPO_ROOT}/shell/tmux/tmux_window_name.py" is-herdr-default-label "$base_label" \
       && [[ "$title_text" != "(no title)" ]]; then
      base_label="${title_text[1,20]}"
    fi
    if [[ -n "$status_emoji" ]]; then
      new_label="${id_emoji}${status_emoji}${base_label}"
    else
      new_label="${base_label}"
    fi

    [[ "$new_label" != "$current_label" ]] && "$herdr_bin" tab rename "$tab_id" "$new_label" >/dev/null 2>&1
  fi
fi

# Only completed (done) or awaiting input (blocked) are worth a notification.
# idle = already-seen completion, working/unknown = nothing to report yet.
case "$agent_status" in
  done|blocked) ;;
  *) exit 0 ;;
esac

# Workspace display number isn't in the context JSON; resolve it with one `workspace list` call.
ws_id="${HERDR_WORKSPACE_ID:-}"
ws_number=""
if [[ -n "$ws_id" ]]; then
  ws_number="$("$herdr_bin" workspace list 2>/dev/null \
    | jq -r --arg w "$ws_id" '.result.workspaces[]? | select(.workspace_id==$w) | .number // empty' 2>/dev/null)"
fi

# screen_label shows workspace:tab display indices; omit entirely if either is missing.
screen_label=""
if [[ -n "$ws_number" && -n "$tab_number" ]]; then
  screen_label=" 🖥️${ws_number}:${tab_number}"
fi

# id_emoji は冒頭のタブアイコン処理で既に決定済み。ここでは通知本文用の
# status_emoji/label_text（done/blocked専用の日本語ラベル）だけ再定義する。
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
