#!/bin/zsh

# GitHub PR number cache for p10k prompt
# Called from my_git_formatter() in .p10k.zsh

# Fast path: read PR number from cache file.
# Sets REPLY to the PR number if found, returns 0.
# Returns 1 if no PR (or not yet fetched).
# Triggers background refresh when cache is missing or stale.
function _gh_pr_cache_read() {
  local repo_root="$VCS_STATUS_WORKDIR"
  local branch="$VCS_STATUS_LOCAL_BRANCH"
  [[ -z $repo_root || -z $branch ]] && return 1

  local cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/zsh/gh-pr"
  local cache_key="${repo_root}:${branch}"
  local cache_file="${cache_dir}/$(/bin/echo -n "$cache_key" | /sbin/md5)"

  if [[ -f $cache_file ]]; then
    local file_mtime file_age
    file_mtime=$(stat -f %m "$cache_file" 2>/dev/null) || file_mtime=0
    file_age=$(( $(date +%s) - file_mtime ))

    # Trigger background refresh when stale (5 minutes)
    if (( file_age > 300 )); then
      _gh_pr_cache_refresh_bg "$repo_root" "$branch" "$cache_file"
    fi

    local pr_num
    pr_num=$(<"$cache_file")
    if [[ -n $pr_num ]]; then
      REPLY=$pr_num
      return 0
    fi
    return 1
  fi

  # No cache: trigger background fetch, return nothing for now
  _gh_pr_cache_refresh_bg "$repo_root" "$branch" "$cache_file"
  return 1
}

# Background refresh: fetch PR number from GitHub API and write to cache.
# Uses a lock file to prevent duplicate concurrent fetches.
function _gh_pr_cache_refresh_bg() {
  local repo_root="$1" branch="$2" cache_file="$3"
  local lock_file="${cache_file}.lock"

  # Skip if already fetching (lock file < 30 seconds old)
  if [[ -f $lock_file ]]; then
    local lock_mtime lock_age
    lock_mtime=$(stat -f %m "$lock_file" 2>/dev/null) || lock_mtime=0
    lock_age=$(( $(date +%s) - lock_mtime ))
    (( lock_age < 30 )) && return
  fi

  # Run in a disowned background subshell to avoid blocking the prompt
  (
    /usr/bin/touch "$lock_file"
    /bin/mkdir -p "${cache_file:h}"

    if ! command -v gh &>/dev/null; then
      /usr/bin/touch "$cache_file"
      /bin/rm -f "$lock_file"
      return
    fi

    local pr_num
    pr_num=$(cd "$repo_root" && gh pr view "$branch" --json number --jq '.number' 2>/dev/null)

    if [[ -n $pr_num && $pr_num == <-> ]]; then
      /bin/echo -n "$pr_num" > "$cache_file"
    else
      /usr/bin/touch "$cache_file"
    fi
    /bin/rm -f "$lock_file"
  ) &!
}
