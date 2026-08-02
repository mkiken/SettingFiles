#!/bin/bash

script_dir="$(builtin cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)" || exit 1
source "${script_dir}/herdr_worktree_context.sh"

worktree_path="$(resolve_herdr_task_worktree_context)" || {
    echo "Herdr worktree context unavailable; lazygit was not started" >&2
    exit 1
}

builtin cd -- "$worktree_path" || exit 1
export XDG_CONFIG_HOME="${HOME}/.config"
exec lazygit
