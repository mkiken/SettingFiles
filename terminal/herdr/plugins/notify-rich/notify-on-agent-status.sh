#!/bin/zsh
# Herdr hook for agent-status, agent-detection, and pane-focus events. Status events
# replace Herdr's plain OS toast with this repository's rich Mac notification;
# every supported event refreshes auto-managed tab labels from the conversation title.
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

# Herdr injects IDs into each event; status and detection events also include agent data.
event_json="${HERDR_PLUGIN_EVENT_JSON:-}"
event_kind="${HERDR_PLUGIN_EVENT:-}"
[[ -z "$event_kind" ]] \
  && event_kind="$(print -r -- "$event_json" | jq -r '.event // empty' 2>/dev/null)"
agent="$(print -r -- "$event_json" \
  | jq -r '.data.agent // .data.pane.agent // empty' 2>/dev/null)"
# `status` is a read-only zsh special parameter (last exit code) — use agent_status instead.
agent_status="$(print -r -- "$event_json" \
  | jq -r '.data.agent_status // .data.pane.agent_status // empty' 2>/dev/null)"

# Gemini has no official Herdr installer integration, so its agent_status is derived
# solely from Herdr's screen-manifest detection and oscillates done<->working<->idle,
# firing this plugin many times per response (tab renames included). Gemini therefore
# opts OUT of the notify-rich single-source model entirely (notification AND tab
# rename) and notifies via its own AfterAgent/Notification tmux hooks
# (ai/gemini/hooks/notification.sh, HERDR guard relaxed there). Claude/Codex report
# status accurately via their installers and stay managed by this plugin.

herdr_bin="${HERDR_BIN_PATH:-herdr}"
pane_id="${HERDR_PANE_ID:-}"
[[ -z "$pane_id" ]] \
  && pane_id="$(print -r -- "$event_json" \
    | jq -r '.data.pane_id // .data.pane.pane_id // empty' 2>/dev/null)"
[[ -z "$pane_id" ]] && exit 0

# 両イベントで同じ最新pane情報を使い、タブ名更新と通知本文の取得経路を一本化する。
pane_json="$("$herdr_bin" pane get "$pane_id" 2>/dev/null)"
[[ -z "$pane_json" ]] && exit 0

[[ -z "$agent" ]] \
  && agent="$(print -r -- "$pane_json" | jq -r '.result.pane.agent // empty' 2>/dev/null)"
[[ "$agent" == "gemini" ]] && exit 0

source "${REPO_ROOT}/shell/tmux/tmux_emoji.conf"

managed_label_state_file() {
  local tab_id="$1"
  local state_root="${HERDR_PLUGIN_STATE_DIR:-}"
  local session_key="${HERDR_SOCKET_PATH:-default}"
  local tab_key="$tab_id"

  [[ -z "$state_root" || -z "$tab_key" ]] && return 1
  session_key="${session_key//[^A-Za-z0-9._-]/_}"
  tab_key="${tab_key//[^A-Za-z0-9._-]/_}"
  print -r -- "${state_root}/tab-labels/${session_key}/${tab_key}"
}

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
    state_file="$(managed_label_state_file "$tab_id")"
    last_auto_label=""
    if [[ -n "$state_file" && -f "$state_file" ]]; then
      IFS= read -r last_auto_label < "$state_file"
    fi

    herdr_default_label=false
    auto_managed=false
    if python3 "${REPO_ROOT}/shell/tmux/tmux_window_name.py" \
        is-herdr-default-label "$base_label"; then
      herdr_default_label=true
      auto_managed=true
    elif [[ -n "$last_auto_label" && "$base_label" == "$last_auto_label" ]]; then
      auto_managed=true
    fi

    # タイトルを会話概要とみなせるのはagent検出paneのみ（Claude/Codexが会話概要を
    # ターミナルタイトルへセットする）。非AI paneのタイトルはNvim等が任意の値
    # （COMMIT_EDITMSG等）をセットするため、タブ名には採用しない。
    title_usable=false
    if [[ -n "$agent" && "$title_text" != "(no title)" ]] \
       && ! python3 "${REPO_ROOT}/shell/tmux/tmux_window_name.py" \
          is-herdr-default-label "$title_text"; then
      title_usable=true
    fi

    record_auto_label=false
    if [[ "$auto_managed" == true && "$title_usable" == true ]]; then
      base_label="${title_text[1,20]}"
      record_auto_label=true
    elif [[ "$herdr_default_label" == true && -n "$last_auto_label" ]]; then
      base_label="$last_auto_label"
    fi
    if [[ -n "$status_emoji" ]]; then
      new_label="${id_emoji}${status_emoji}${base_label}"
    else
      new_label="${base_label}"
    fi

    rename_ok=true
    if [[ "$new_label" != "$current_label" ]] \
       && ! "$herdr_bin" tab rename "$tab_id" "$new_label" >/dev/null 2>&1; then
      rename_ok=false
    fi

    if [[ "$record_auto_label" == true && "$rename_ok" == true && -n "$state_file" \
          && "$base_label" != "$last_auto_label" ]]; then
      state_dir="${state_file:h}"
      if mkdir -p "$state_dir" 2>/dev/null; then
        print -r -- "$base_label" >| "$state_file" 2>/dev/null
      fi
    fi
  fi
fi

# Only completed (done) or awaiting input (blocked) are worth a notification.
# idle = already-seen completion, working/unknown = nothing to report yet.
case "$event_kind" in
  pane.agent_status_changed|pane_agent_status_changed) ;;
  *) exit 0 ;;
esac
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
