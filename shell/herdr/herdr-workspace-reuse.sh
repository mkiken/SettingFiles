#!/bin/bash

# Named workspace creation proxy. Herdr's automatic index is display-only.
set -euo pipefail

real_bin="${HERDR_REAL_BIN_PATH:-${HERDR_BIN_PATH:-herdr}}"
[[ "$real_bin" != "$0" ]] || { echo 'HERDR_REAL_BIN_PATH points to the proxy' >&2; exit 1; }

if [[ "${1:-}" != workspace || "${2:-}" != create ]]; then
    exec "$real_bin" "$@"
fi

create_args=("$@")
shift 2
label=""
focus=0
while (( $# )); do
    case "$1" in
        --label)
            (( $# >= 2 )) || { echo 'workspace label is missing' >&2; exit 2; }
            label="$2"
            shift 2
            ;;
        --focus) focus=1; shift ;;
        --no-focus) focus=0; shift ;;
        *) shift ;;
    esac
done

if [[ -z "$label" ]]; then
    exec "$real_bin" "${create_args[@]}"
fi

list_json=$("$real_bin" workspace list) || exit $?
if ! jq -e '.result.workspaces | type == "array"' >/dev/null <<< "$list_json"; then
    echo 'herdr workspace list returned invalid JSON' >&2
    exit 1
fi

workspace=$(jq -c --arg label "$label" '
    [.result.workspaces[]
     | select((.label | sub("^\\[[0-9]+\\] "; "")) == $label)]
    | sort_by([if .focused then 0 else 1 end, .number]) | first // empty
' <<< "$list_json") || exit $?

if [[ -n "$workspace" ]]; then
    workspace_id=$(jq -r '.workspace_id // empty' <<< "$workspace")
    [[ -n "$workspace_id" ]] || { echo 'matching workspace has no ID' >&2; exit 1; }
    if (( focus )); then
        "$real_bin" workspace focus "$workspace_id" >/dev/null || exit $?
    fi
    jq -nc --argjson workspace "$workspace" \
        '{result: {workspace: $workspace, reused: true}}'
    exit 0
fi

created=$("$real_bin" "${create_args[@]}") || exit $?
if ! jq -e '.result.workspace.workspace_id | type == "string" and length > 0' >/dev/null <<< "$created"; then
    echo 'herdr workspace create returned invalid JSON' >&2
    exit 1
fi
jq -c '.result.reused = false' <<< "$created"
