#!/usr/bin/env bash
# Render a PR diff with explicit current-side line numbers for review prompts.

set -euo pipefail

usage() {
  printf 'Usage: %s [--stdin] [PR_NUMBER|URL|BRANCH]\n' "${0##*/}" >&2
}

input_mode="pr"
pr_ref=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --stdin)
      input_mode="stdin"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      if [[ -n "${pr_ref}" ]]; then
        usage
        exit 2
      fi
      pr_ref="$1"
      ;;
  esac
  shift
done

emit_diff() {
  if [[ "${input_mode}" == "stdin" ]]; then
    /bin/cat
    return
  fi

  if [[ -n "${pr_ref}" ]]; then
    gh pr diff "${pr_ref}" --patch --color=never
  else
    gh pr diff --patch --color=never
  fi
}

parse_diff() {
  local line old_path new_path current_file
  local old_line=0 new_line=0 in_hunk=0

  while IFS= read -r line || [[ -n "${line}" ]]; do
    if [[ "${line}" == diff\ --git\ * ]]; then
      old_path=""
      new_path=""
      current_file=""
      in_hunk=0
      continue
    fi

    if [[ "${line}" == "--- "* ]]; then
      old_path="${line#--- }"
      [[ "${old_path}" == a/* ]] && old_path="${old_path#a/}"
      continue
    fi

    if [[ "${line}" == "+++ "* ]]; then
      new_path="${line#+++ }"
      if [[ "${new_path}" == b/* ]]; then
        current_file="${new_path#b/}"
      elif [[ "${new_path}" == "/dev/null" ]]; then
        current_file="${old_path}"
      else
        current_file="${new_path}"
      fi
      printf 'FILE %s\n' "${current_file}"
      if [[ "${new_path}" == "/dev/null" ]]; then
        printf 'DELETED_FILE %s\n' "${current_file}"
      fi
      continue
    fi

    if [[ "${line}" =~ ^@@[[:space:]]-([0-9]+)(,([0-9]+))?[[:space:]]\+([0-9]+)(,([0-9]+))?[[:space:]]@@ ]]; then
      old_line="${BASH_REMATCH[1]}"
      new_line="${BASH_REMATCH[4]}"
      in_hunk=1
      printf '%s\n' "${line}"
      continue
    fi

    if [[ "${in_hunk}" -ne 1 ]]; then
      continue
    fi

    case "${line:0:1}" in
      " ")
        printf 'CTX %s %s\n' "${new_line}" "${line:1}"
        old_line=$((old_line + 1))
        new_line=$((new_line + 1))
        ;;
      "+")
        printf 'NEW %s %s\n' "${new_line}" "${line:1}"
        new_line=$((new_line + 1))
        ;;
      "-")
        printf 'OLD %s %s\n' "${old_line}" "${line:1}"
        old_line=$((old_line + 1))
        ;;
      "\\")
        ;;
      *)
        in_hunk=0
        ;;
    esac
  done
}

emit_diff | parse_diff
