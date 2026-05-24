#!/bin/zsh
# Open a tmux window or session from zoxide's interactive directory picker.

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

set -u

function _usage() {
  echo "Usage: tmux-cdi-open.zsh <window|session>" >&2
}

function _select_cdi_path() {
  if ! command -v zoxide >/dev/null 2>&1; then
    echo "zoxide が見つかりません" >&2
    return 1
  fi

  local target_path
  target_path=$(zoxide query --interactive --) || return 130
  [[ -n "$target_path" && -d "$target_path" ]] || return 1

  print -r -- "$target_path"
}

function main() {
  local mode="${1:-}"
  if [[ "$mode" != "window" && "$mode" != "session" ]]; then
    _usage
    return 2
  fi

  local set_dir="${SET:-$HOME/Desktop/repository/SettingFiles/}"
  local tmux_alias_file="${set_dir}shell/zsh/alias/tmux.zsh"
  if [[ ! -r "$tmux_alias_file" ]]; then
    echo "tmux alias file not found: $tmux_alias_file" >&2
    return 1
  fi

  source "$tmux_alias_file"

  if ! _tmux_require_client; then
    return 1
  fi

  local target_path
  target_path=$(_select_cdi_path) || return $?

  case "$mode" in
  window)
    _tmux_create_window_at_path "$target_path"
    ;;
  session)
    _tmux_create_session_at_path "$target_path"
    ;;
  esac
}

main "$@"
