#!/bin/zsh

# Start the preferred multiplexer from any interactive shell that isn't
# already nested inside one. A return code of 10 tells managed.zsh to stop
# loading the outer shell after a successful multiplexer run. Other return
# codes keep the current shell usable.
function auto_start_terminal_multiplexer() {
  local is_tmux="${1:-false}"
  local is_warp="${2:-false}"
  local exit_code=0

  if [[ "${HERDR_ENV:-}" == "1" ]] \
     || [[ "$is_tmux" == "true" ]] \
     || [[ "$is_warp" == "true" ]]; then
    return 0
  fi

  if command -v herdr >/dev/null 2>&1; then
    TMUX= TMUX_PANE= herdr
    exit_code=$?
    if (( exit_code != 0 )); then
      print -u2 -- "Herdr exited with status ${exit_code}; continuing in the current shell."
      return 0
    fi
    return 10
  fi

  if command -v tmux >/dev/null 2>&1; then
    TMUX= TMUX_PANE= tmux new-session -A -s tmux \; set-option window-size largest
    return 10
  fi

  print -u2 -- "Herdr and tmux are not installed; continuing without a multiplexer."
  return 0
}
