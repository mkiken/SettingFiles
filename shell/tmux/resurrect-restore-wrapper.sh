#!/usr/bin/env bash

set -euo pipefail

RESURRECT_RESTORE_SCRIPT="${TMUX_RESURRECT_RESTORE_SCRIPT:-$HOME/.tmux/plugins/tmux-resurrect/scripts/restore.sh}"

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

display_message() {
  tmux display-message "$1" 2>/dev/null || printf '%s\n' "$1" >&2
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
  local dir="$1"
  local marker="$2"
  local target

  target="$(snapshot_target "$marker")" || return 1
  if [[ "$target" = /* ]]; then
    [[ -f "$target" ]] || return 1
    printf '%s\n' "$target"
    return 0
  else
    [[ -f "${dir}/${target}" ]] || return 1
    printf '%s/%s\n' "$dir" "$target"
  fi
}

snapshot_time() {
  local file="$1"
  local timestamp

  if timestamp="$(stat -f '%Sm' -t '%Y-%m-%d %H:%M' "$file" 2>/dev/null)"; then
    printf '%s\n' "$timestamp"
    return 0
  fi

  if timestamp="$(stat -c '%y' "$file" 2>/dev/null)"; then
    printf '%s\n' "${timestamp:0:16}"
    return 0
  fi

  return 1
}

menu_label() {
  local kind="$1"
  local dir="$2"
  local marker="${dir}/last-${kind}"
  local title="$3"
  local file
  local timestamp

  if [[ "$kind" == "auto" && ! -e "$marker" && ! -e "${dir}/last-manual" ]]; then
    marker="${dir}/last"
  fi

  if file="$(snapshot_file "$dir" "$marker" 2>/dev/null)" && [[ -f "$file" ]]; then
    timestamp="$(snapshot_time "$file" 2>/dev/null || true)"
    if [[ -n "$timestamp" ]]; then
      printf '%s (%s)\n' "$title" "$timestamp"
      return 0
    fi
  fi

  printf '%s (missing)\n' "$title"
}

show_menu() {
  local dir
  local script
  local manual_label
  local auto_label

  dir="$(resurrect_dir)"
  script="${BASH_SOURCE[0]}"
  manual_label="$(menu_label "manual" "$dir" "Manual snapshot")"
  auto_label="$(menu_label "auto" "$dir" "Auto snapshot")"

  tmux display-menu -T "Restore tmux snapshot" \
    "$manual_label" M "run-shell '$script manual'" \
    "$auto_label" A "run-shell '$script auto'" \
    "" "" "" \
    "Cancel" q ""
}

activate_snapshot() {
  local kind="$1"
  local dir="$2"
  local marker="${dir}/last-${kind}"
  local pane_snapshot="${dir}/pane_contents.${kind}.tar.gz"
  local target

  if [[ "$kind" == "auto" && ! -e "$marker" && ! -e "${dir}/last-manual" ]]; then
    marker="${dir}/last"
    pane_snapshot="${dir}/pane_contents.tar.gz"
  fi

  snapshot_file "$dir" "$marker" >/dev/null || return 1
  target="$(snapshot_target "$marker")" || return 1
  ln -sfn "$target" "${dir}/last"

  if [[ "$pane_snapshot" == "${dir}/pane_contents.tar.gz" ]]; then
    return 0
  fi

  if [[ -f "$pane_snapshot" ]]; then
    cp -f "$pane_snapshot" "${dir}/pane_contents.tar.gz"
  else
    rm -f "${dir}/pane_contents.tar.gz"
  fi
}

restore_snapshot() {
  local kind="$1"
  local dir

  dir="$(resurrect_dir)"
  if ! activate_snapshot "$kind" "$dir"; then
    display_message "No ${kind} tmux snapshot"
    return 1
  fi

  display_message "Restoring ${kind} tmux snapshot..."
  "$RESURRECT_RESTORE_SCRIPT"
}

main() {
  case "${1:-menu}" in
    menu)
      show_menu
      ;;
    manual | auto)
      restore_snapshot "$1"
      ;;
    *)
      printf 'Usage: %s [menu|manual|auto]\n' "$0" >&2
      return 2
      ;;
  esac
}

main "$@"
