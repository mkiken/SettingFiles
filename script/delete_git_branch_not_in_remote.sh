#!/bin/sh

function delete_git_branch_not_in_remote() {
  cd $1

  local tmp_path=$(git rev-parse --show-toplevel 2>/dev/null)
  if [ -n "$tmp_path" ]; then
    local repo_name=`basename $tmp_path`
    echo "repository is '$repo_name'."
  else
    echo "$1 is not git repository."
    exit 1
  fi
  git fetch --prune

  local local_branches=`git branch | grep -v '*'`
  local remote_branches=`git branch -r | grep -v '\->' | sed -e 's/origin\///'`
  for local_branch in $local_branches
  do
    local is_in_remote=false
    for remote_branch in $remote_branches
    do
      if [[ "$local_branch" = "$remote_branch" ]]; then
        is_in_remote=true
        break
      fi
    done

    if [[ $is_in_remote = false ]]; then
      echo "branch '$local_branch' is not in remote. delete it? [y/N]"

      exec < /dev/tty
      read ANSWER

      case $ANSWER in
        "Y" | "y" | "yes" | "Yes" | "YES" ) git branch -D $local_branch;;
        * ) echo "not delete branch '$local_branch'.";;
      esac
    fi
  done

  cd $OLDPWD
}

delete_git_branch_not_in_remote $1
