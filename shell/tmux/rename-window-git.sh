#!/bin/bash
# Rename the current tmux window to "reponame:branch" (fish-style branch abbreviation)
# or just "dirname" if not in a git repository.
#
# Usage: rename-window-git.sh <path>

TARGET_PATH="${1:-$PWD}"

cd "$TARGET_PATH" || exit 1

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)

if [ -z "$REPO_ROOT" ]; then
  tmux rename-window "$(basename "$TARGET_PATH")"
  exit 0
fi

REPO_NAME=$(basename "$REPO_ROOT")
BRANCH=$(git branch --show-current 2>/dev/null)

if [ -z "$BRANCH" ]; then
  # detached HEAD: show short SHA
  BRANCH=$(git rev-parse --short HEAD 2>/dev/null)
fi

# Fish-style abbreviation: shorten all segments except the last to 1 char
fish_abbrev() {
  local branch="$1"
  local IFS='/'
  read -ra segments <<< "$branch"
  local count="${#segments[@]}"

  if [ "$count" -le 1 ]; then
    echo "$branch"
    return
  fi

  local result=""
  for ((i = 0; i < count - 1; i++)); do
    result+="${segments[$i]:0:1}/"
  done
  result+="${segments[$((count - 1))]}"
  echo "$result"
}

# Truncate the last segment if it exceeds 20 chars
truncate_last() {
  local branch="$1"
  local max=20
  local last="${branch##*/}"
  local prefix="${branch%/*}"

  if [ "${#last}" -gt "$max" ]; then
    last="${last:0:$max}…"
  fi

  if [ "$prefix" = "$branch" ]; then
    echo "$last"
  else
    echo "${prefix}/${last}"
  fi
}

ABBREV=$(fish_abbrev "$BRANCH")
ABBREV=$(truncate_last "$ABBREV")

tmux rename-window "${REPO_NAME}:${ABBREV}"
