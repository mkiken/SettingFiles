#!/usr/bin/env bash

set -euo pipefail

tmux set-option -gq @resurrect-save-script-path "$HOME/.tmux/scripts/resurrect-save-wrapper.sh"
tmux bind-key C-s run-shell "$HOME/.tmux/scripts/resurrect-save-wrapper.sh"
tmux bind-key C-r run-shell "$HOME/.tmux/scripts/resurrect-restore-wrapper.sh menu"
