#!/bin/zsh

_herdr_wtc_pause() {
  # 共通ラッパー(herdr-popup-run.sh)へpause済みを通知し二重待ちを防ぐ
  [[ -n "${HERDR_POPUP_PAUSE_MARK:-}" ]] && print -r -- "create-worktree-tab" >> "${HERDR_POPUP_PAUSE_MARK}" 2>/dev/null
  [[ -t 0 ]] || return 0
  read -k 1 "?Press any key to close..."
  print
}

if [[ -n "${HERDR_BIN_PATH:-}" ]]; then
  herdr() {
    command "$HERDR_BIN_PATH" "$@"
  }
fi

if [[ "${HERDR_ENV:-}" != "1" ]]; then
  echo "herdr worktree: HERDR_ENV is not set" >&2
  return 1
fi

active_pane_id="${HERDR_ACTIVE_PANE_ID:-}"
active_pane_cwd="${HERDR_ACTIVE_PANE_CWD:-}"
if [[ -z "$active_pane_id" || -z "$active_pane_cwd" ]]; then
  echo "herdr worktree: active pane context is unavailable" >&2
  _herdr_wtc_pause
  return 1
fi

workspace_id="${active_pane_id%%:*}"
if [[ -z "$workspace_id" || "$workspace_id" == "$active_pane_id" ]]; then
  echo "herdr worktree: invalid active pane id: $active_pane_id" >&2
  _herdr_wtc_pause
  return 1
fi

if ! builtin cd "$active_pane_cwd"; then
  echo "herdr worktree: cannot enter active pane directory" >&2
  _herdr_wtc_pause
  return 1
fi

branch=""
read -r "branch?New worktree branch: " || return 0
[[ -z "$branch" ]] && return 0

wtc "$branch"
wtc_status=$?
if (( wtc_status != 0 )); then
  _herdr_wtc_pause
  return "$wtc_status"
fi

_herdr_run_in_new_tab "$workspace_id" "$PWD" "$branch" ":" "" 1
tab_status=$?
if (( tab_status != 0 )); then
  _herdr_wtc_pause
  return "$tab_status"
fi
