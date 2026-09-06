#!/bin/bash

_herdr_worktree_context_bin() {
    printf '%s\n' "${HERDR_BIN_PATH:-herdr}"
}

_herdr_worktree_context_tab_id() {
    if [[ -n "${HERDR_TAB_ID:-}" ]]; then
        printf '%s\n' "$HERDR_TAB_ID"
        return 0
    fi

    [[ -n "${HERDR_PANE_ID:-}" ]] || return 1
    "$(_herdr_worktree_context_bin)" pane get "$HERDR_PANE_ID" 2>/dev/null \
        | jq -r '.result.pane.tab_id // empty' 2>/dev/null
}

_herdr_worktree_context_active_tab_id() {
    [[ -n "${HERDR_ACTIVE_PANE_ID:-}" ]] || return 1
    "$(_herdr_worktree_context_bin)" pane get "$HERDR_ACTIVE_PANE_ID" 2>/dev/null \
        | jq -r '.result.pane.tab_id // empty' 2>/dev/null
}

_herdr_worktree_context_state_file() {
    local tab_id="$1"
    [[ -n "$tab_id" ]] || return 1

    local session_key="${HERDR_SOCKET_PATH:-default}"
    session_key="${session_key//[^A-Za-z0-9._-]/_}"
    local tab_key="${tab_id//[^A-Za-z0-9._-]/_}"
    printf '%s\n' "${XDG_CACHE_HOME:-$HOME/.cache}/herdr-task-worktree/${session_key}/${tab_key}"
}

_herdr_worktree_context_valid_path() {
    local worktree_path="$1"
    [[ -d "$worktree_path" ]] \
        && git -C "$worktree_path" rev-parse --is-inside-work-tree >/dev/null 2>&1
}

set_herdr_task_worktree_context() {
    local worktree_path="$1"
    [[ -n "${HERDR_ENV:-}" || -n "${HERDR_PANE_ID:-}" ]] || return 0
    _herdr_worktree_context_valid_path "$worktree_path" || return 1

    local tab_id
    tab_id="$(_herdr_worktree_context_tab_id)" || return 1
    [[ -n "$tab_id" ]] || return 1

    local state_file
    state_file="$(_herdr_worktree_context_state_file "$tab_id")" || return 1
    local state_dir
    state_dir="$(dirname "$state_file")" || return 1
    mkdir -p "$state_dir" || return 1

    local temporary_file="${state_file}.$$"
    (umask 077 && printf '%s\n' "$worktree_path" >"$temporary_file") || return 1
    mv -f "$temporary_file" "$state_file"
}

clear_herdr_task_worktree_context() {
    [[ -n "${HERDR_ENV:-}" || -n "${HERDR_PANE_ID:-}" ]] || return 0

    local tab_id
    tab_id="$(_herdr_worktree_context_tab_id)" || return 1
    [[ -n "$tab_id" ]] || return 1

    local state_file
    state_file="$(_herdr_worktree_context_state_file "$tab_id")" || return 1
    [[ -e "$state_file" ]] || return 0
    trash "$state_file"
}

resolve_herdr_task_worktree_context() {
    local tab_id
    tab_id="$(_herdr_worktree_context_active_tab_id)" || tab_id=""

    if [[ -n "$tab_id" ]]; then
        local state_file
        state_file="$(_herdr_worktree_context_state_file "$tab_id")" || return 1
        if [[ -f "$state_file" ]]; then
            local worktree_path
            IFS= read -r worktree_path <"$state_file" || worktree_path=""
            if _herdr_worktree_context_valid_path "$worktree_path"; then
                printf '%s\n' "$worktree_path"
                return 0
            fi
            trash "$state_file"
        fi
    fi

    [[ -n "${HERDR_ACTIVE_PANE_CWD:-}" && -d "${HERDR_ACTIVE_PANE_CWD}" ]] || return 1
    printf '%s\n' "$HERDR_ACTIVE_PANE_CWD"
}
