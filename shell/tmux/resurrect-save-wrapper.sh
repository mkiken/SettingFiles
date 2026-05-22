#!/usr/bin/env bash

set -euo pipefail

RESURRECT_SAVE_SCRIPT="${TMUX_RESURRECT_SAVE_SCRIPT:-$HOME/.tmux/plugins/tmux-resurrect/scripts/save.sh}"

resurrect_dir() {
  local path

  path="$(tmux show-option -gqv @resurrect-dir 2>/dev/null || true)"
  if [[ -z "$path" ]]; then
    if [[ -d "$HOME/.tmux/resurrect" ]]; then
      path="$HOME/.tmux/resurrect"
    else
      path="${XDG_DATA_HOME:-$HOME/.local/share}/tmux/resurrect"
    fi
  fi

  path="${path/#\~/$HOME}"
  path="${path//\$HOME/$HOME}"
  path="${path//\$HOSTNAME/$(hostname)}"
  printf '%s\n' "$path"
}

snapshot_target() {
  local marker="$1"
  local target

  if [[ -L "$marker" ]]; then
    target="$(readlink "$marker")"
    printf '%s\n' "$target"
    return 0
  fi

  if [[ -f "$marker" ]]; then
    printf '%s\n' "$(basename "$marker")"
    return 0
  fi

  return 1
}

snapshot_file() {
  local marker="$1"
  local dir
  local target

  target="$(snapshot_target "$marker")" || return 1
  if [[ "$target" = /* ]]; then
    [[ -f "$target" ]] || return 1
    printf '%s\n' "$target"
    return 0
  fi

  dir="$(dirname "$marker")"
  [[ -f "${dir}/${target}" ]] || return 1
  printf '%s/%s\n' "$dir" "$target"
}

activate_snapshot() {
  local kind="$1"
  local dir="$2"
  local marker="${dir}/last-${kind}"
  local pane_snapshot="${dir}/pane_contents.${kind}.tar.gz"
  local target

  snapshot_file "$marker" >/dev/null || return 1
  target="$(snapshot_target "$marker")" || return 1
  ln -sfn "$target" "${dir}/last"

  if [[ -f "$pane_snapshot" ]]; then
    cp -f "$pane_snapshot" "${dir}/pane_contents.tar.gz"
  else
    rm -f "${dir}/pane_contents.tar.gz"
  fi
}

record_snapshot() {
  local kind="$1"
  local dir="$2"
  local last_file="${dir}/last"
  local marker="${dir}/last-${kind}"
  local pane_current="${dir}/pane_contents.tar.gz"
  local pane_snapshot="${dir}/pane_contents.${kind}.tar.gz"
  local source_file

  mkdir -p "$dir"

  source_file="$(snapshot_file "$last_file")" || return 1
  if [[ ! -e "$marker" || ! "$source_file" -ef "$marker" ]]; then
    cp -f "$source_file" "$marker"
  fi

  if [[ -f "$pane_current" ]]; then
    cp -f "$pane_current" "$pane_snapshot"
  else
    rm -f "$pane_snapshot"
  fi
}

main() {
  local kind="manual"
  local dir

  if [[ "${1:-}" == "quiet" ]]; then
    kind="auto"
  fi

  "$RESURRECT_SAVE_SCRIPT" "$@"

  dir="$(resurrect_dir)"
  record_snapshot "$kind" "$dir"

  if [[ "$kind" == "manual" ]]; then
    activate_snapshot "manual" "$dir"
  elif [[ -e "${dir}/last-manual" ]]; then
    activate_snapshot "manual" "$dir"
  fi
}

main "$@"
