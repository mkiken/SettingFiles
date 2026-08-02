#!/bin/zsh
# Git aliases

# gitブランチ表記をクリーンアップする共通関数
# `*` (現在のブランチ) と `+` (worktreeで使用中のブランチ) をフィルター
function _clean_git_branch_markers() {
  sed -e 's/[*+]//'
}

# Disable Side-by-side
alias -g DS='GIT_PAGER="delta --no-gitconfig --diff-so-fancy --paging=always"'

alias cdgr='cd `g repository`'
alias g='noglob git'
alias ga='git add'
alias gaa='ga .'
alias gb='no_notify git branch'
alias gbD='gb -D'
alias gba='gb -a'
alias gbd='gb -d'
alias gca='gci --amend'
alias gcb='git current-branch'
alias gcbc='gcb | tr -d "\n" | pc;echo'
alias gcf='g conflicts'
alias gci='no_notify git ci'
alias gcl='g cl'
alias gcln='gcl -n'
alias gcm='gci -m'
alias gco='git co'
alias gcoo='gco --ours'
alias gcot='gco --theirs'
alias gcp='g cp'
alias gd='no_notify git diff'
alias gdc='gd --cached'
alias gdn='gd --name-status'
alias gfp='git fetch --all --prune'
alias gl='no_notify git log'
alias gln='gl --name-status'
alias glst='gl --stat'
alias glp='gl -p'
alias gmg='git merge'
alias gmgs='gmg --squash'
alias gpl='g pl'
alias gps='git push -u'
alias grm='g rm'
alias grv='g rv'
alias gs='git s'
alias gsa='g s -s --porcelain | grep "^ A"'
alias gsd='g s -s --porcelain | grep "^ D"'
alias gsm='g s -s --porcelain | grep "^ M"'
alias gsu='g s -s --porcelain | grep "^?"'
alias gsw='g sw'
gswc() {
  noglob git sw --no-track -c "$@"
}
alias gmt='no_notify git mt'
alias gst='git st'
alias gstd='gst drop'
alias gstp='gst pop'
alias gsts='gst show'
alias gstu='gst -u'
alias gprb='gpl --rebase'

# Git blame with color
function gbl(){
  git bl "${@}" | gsed -f "${SET}sedfiles/colorize_git_blame.sed" | less
}

# Git branch rename
function gbm(){
  branch=$(git current-branch)
  git branch -m "${branch}" "${@}"
}

# Git branch cleanup functions
alias g-delete-remote-merged-branches="g-remote-merged-branches | xargs -I% git push origin :%"
alias g-remote-merged-branches="git branch -a --merged | 'grep' -v '*' | 'grep' -v master | 'grep' remotes/origin/ | sed -e 's% *remotes/origin/%%'"
alias g-remote-merged-branches_orig="git branch -a --merged | 'grep' -v '*' | 'grep' -v master | 'grep' remotes/origin/"

alias g-delete-remote-merged-branches-dry-run="g-remote-merged-branches | xargs -I% git push -n origin :% 2>&1 | tee -a ~/Desktop/delete_branches_dry_run.log"
alias g-delete-remote-merged-branches="g-remote-merged-branches | xargs -I% git push origin :% 2>&1 | tee -a ~/Desktop/delete_branches.log"

alias g-delete-remote-branches-hash-check="g-remote-merged-branches_orig | xargs -I{} sh -c 'echo {};git rev-parse {};echo ""' 2>&1 | tee -a ~/Desktop/delete_branches_hash_check.txt"

alias g-merged-branches="git merged-branches | grep -vE '^\*|master$|develop$'"
alias g-delete-merged-branches="g-merged-branches | xargs -I% git branch -d %"

# Git branch functions
function g-remote-branches-by-word(){
  git branch -a | grep -v '*' | grep -v master | grep "$1" | grep remotes/origin/
}

function g-remote-branches-by-word-fmt(){
  g-remote-branches-by-word "$1" | sed -e 's% *remotes/origin/%%'
}

function g-delete-remote-branches-by-word-hash-check() {
  g-remote-branches-by-word "$1" | xargs -I{} sh -c 'echo {};git rev-parse {};echo ""' 2>&1 | tee -a ~/Desktop/delete_branches_hash_check.txt
}

function g-delete-remote-branches-by-word-dry-run() {
  g-remote-branches-by-word-fmt "$1" | xargs -I% git push -n origin :% 2>&1 | tee -a ~/Desktop/delete_branches_dry_run.log
}

function g-delete-remote-branches-by-word() {
  g-remote-branches-by-word-fmt "$1" | xargs -I% git push origin :% 2>&1 | tee -a ~/Desktop/delete_branches.log
}

function g-delete-branch-not-in-remote-interactive() {
  # レポジトリ名確認
  local tmp_path=$(git rev-parse --show-toplevel 2>/dev/null)
  if [ -n "${tmp_path}" ]; then
    local repo_name=$(basename "${tmp_path}")
    echo "repository is '${repo_name}'."
  else
    echo "$1 is not git repository."
    return 1
  fi

  # 最新のリモート情報をフェッチ
  git fetch --prune

  # ローカルブランチ（現在のブランチとworktreeブランチは除外）
  local local_branches=( $(git branch | _clean_git_branch_markers) )
  # リモートブランチ（「origin/HEAD -> origin/master」の行を除外し、「origin/」を消す）
  local remote_branches=( $(git branch -r | grep -v '\->' -p | sed -e 's/origin\///') )

  # 削除候補を収集
  local branches_to_delete=()
  for local_branch in ${local_branches}
  do
    # ローカルブランチがリモートにあるか確認
    local is_in_remote=false
    for remote_branch in ${remote_branches}
    do
      if [[ "${local_branch}" = "${remote_branch}" ]]; then
        is_in_remote=true
        break
      fi
    done

    # リモートになかったら削除候補に追加
    if [[ ${is_in_remote} = false ]]; then
      branches_to_delete+=("${local_branch}")
    fi
  done

  # 候補がなければ終了
  if [[ ${#branches_to_delete[@]} -eq 0 ]]; then
    echo "No branches to delete."
    return 0
  fi

  # 削除候補を一覧表示
  echo ""
  echo "=== Branches not in remote (${#branches_to_delete[@]} branches) ==="
  for branch in ${branches_to_delete}
  do
    echo "  - ${branch}"
  done
  echo ""

  # 一括削除の確認
  echo "Delete all ${#branches_to_delete[@]} branches? [y/N]"
  read -r ANSWER

  case ${ANSWER} in
    "Y" | "y" | "yes" | "Yes" | "YES" )
      for branch in ${branches_to_delete}
      do
        git branch -D "${branch}"
      done
      return 0
      ;;
  esac

  # 個別に確認
  for branch in ${branches_to_delete}
  do
    echo "Delete branch '${branch}'? [y/N]"
    read -r ANSWER

    case ${ANSWER} in
      "Y" | "y" | "yes" | "Yes" | "YES" )
        git branch -D "${branch}"
        ;;
      * )
        echo "Skipped: ${branch}"
        ;;
    esac
  done
}

# difit は Node>=21 を要求するが、プロジェクトの mise 設定（.mise.toml）が古い Node に固定していると
# SyntaxError でクラッシュする。homebrew_run で brew の node を優先して起動する。
di() {
  no_notify homebrew_run difit "$@"
}

alias dia='di --include-untracked .'
alias diw='di working'
alias dis='di staged'

wtc() {
  wt switch --create "$@"
}

wtl() {
  wt list "$@"
}

wts() {
  wt switch "$@"
}

wtr() {
  if (( $# == 0 )); then
    wt switch
  else
    wt remove "$@"
  fi
}

# Merge the current secondary worktree branch into the worktree that has the
# requested local branch checked out. Cleanup runs only after a successful merge.
wtm() {
  if (( $# != 1 )) || [[ -z "$1" ]]; then
    echo "Usage: wtm <target-branch>" >&2
    return 2
  fi

  local target_branch="$1"
  local source_path
  source_path=$(git rev-parse --show-toplevel) || return $?
  source_path=$(builtin cd -q "$source_path" && pwd -P) || return $?

  local source_branch
  source_branch=$(git symbolic-ref --quiet --short HEAD)
  local source_branch_status=$?
  if [[ $source_branch_status -ne 0 ]] || [[ -z "$source_branch" ]]; then
    echo "detached HEAD cannot be merged with wtm" >&2
    return 1
  fi

  local worktree_list
  worktree_list=$(git worktree list --porcelain) || return $?

  local primary_path
  primary_path=$(print -r -- "$worktree_list" | sed -n '1s/^worktree //p')
  if [[ -z "$primary_path" ]]; then
    echo "primary worktree could not be resolved" >&2
    return 1
  fi
  primary_path=$(builtin cd -q "$primary_path" && pwd -P) || return $?
  if [[ "$source_path" == "$primary_path" ]]; then
    echo "wtm cannot merge from the primary worktree" >&2
    return 1
  fi

  if [[ "$source_branch" == "$target_branch" ]]; then
    echo "source and target branches must differ" >&2
    return 1
  fi

  local source_head
  source_head=$(git -C "$source_path" rev-parse --verify "HEAD^{commit}") || return $?

  local target_ref="refs/heads/${target_branch}"
  local target_matches
  target_matches=$(print -r -- "$worktree_list" | awk -v target_ref="$target_ref" '
    /^worktree / { worktree_path = substr($0, 10); next }
    $0 == "branch " target_ref { print worktree_path }
  ')

  local -a target_paths
  if [[ -n "$target_matches" ]]; then
    target_paths=("${(@f)target_matches}")
  else
    target_paths=()
  fi

  if (( ${#target_paths[@]} == 0 )); then
    echo "target branch is not checked out in a worktree: $target_branch" >&2
    return 1
  fi
  if (( ${#target_paths[@]} > 1 )); then
    echo "target branch is checked out in multiple worktrees: $target_branch" >&2
    return 1
  fi

  local target_path="${target_paths[1]}"
  target_path=$(git -C "$target_path" rev-parse --show-toplevel) || return $?
  target_path=$(builtin cd -q "$target_path" && pwd -P) || return $?

  local target_current_branch
  target_current_branch=$(git -C "$target_path" symbolic-ref --quiet --short HEAD)
  local target_branch_status=$?
  if [[ $target_branch_status -ne 0 ]] || [[ "$target_current_branch" != "$target_branch" ]]; then
    echo "target worktree branch changed before merge" >&2
    return 1
  fi

  local target_head
  target_head=$(git -C "$target_path" rev-parse --verify "HEAD^{commit}") || return $?

  local source_status_output
  source_status_output=$(git -C "$source_path" status --porcelain)
  local source_status_exit=$?
  if [[ $source_status_exit -ne 0 ]]; then
    echo "failed to inspect source worktree status" >&2
    return $source_status_exit
  fi
  if [[ -n "$source_status_output" ]]; then
    echo "source worktree has uncommitted changes" >&2
    return 1
  fi

  local target_status_output
  target_status_output=$(git -C "$target_path" status --porcelain)
  local target_status_exit=$?
  if [[ $target_status_exit -ne 0 ]]; then
    echo "failed to inspect target worktree status" >&2
    return $target_status_exit
  fi
  if [[ -n "$target_status_output" ]]; then
    echo "target worktree has uncommitted changes" >&2
    return 1
  fi

  local verified_source_branch_head
  verified_source_branch_head=$(git rev-parse --verify "refs/heads/${source_branch}^{commit}" 2>/dev/null)
  if [[ "$verified_source_branch_head" != "$source_head" ]]; then
    echo "source branch changed before merge" >&2
    return 1
  fi

  local verified_source_worktree_head
  verified_source_worktree_head=$(git -C "$source_path" rev-parse --verify "HEAD^{commit}" 2>/dev/null)
  if [[ "$verified_source_worktree_head" != "$source_head" ]]; then
    echo "source worktree HEAD changed before merge" >&2
    return 1
  fi

  local verified_target_branch
  verified_target_branch=$(git -C "$target_path" symbolic-ref --quiet --short HEAD 2>/dev/null)
  if [[ "$verified_target_branch" != "$target_branch" ]]; then
    echo "target worktree branch changed before merge" >&2
    return 1
  fi

  local verified_target_head
  verified_target_head=$(git -C "$target_path" rev-parse --verify "HEAD^{commit}" 2>/dev/null)
  if [[ "$verified_target_head" != "$target_head" ]]; then
    echo "target worktree HEAD changed before merge" >&2
    return 1
  fi

  git -C "$target_path" merge --no-edit -- "$source_head" || return $?

  local cleanup_target_branch
  cleanup_target_branch=$(git -C "$target_path" symbolic-ref --quiet --short HEAD 2>/dev/null)
  if [[ "$cleanup_target_branch" != "$target_branch" ]]; then
    echo "target worktree branch changed after merge; cleanup stopped" >&2
    return 1
  fi

  local cleanup_target_status_output
  cleanup_target_status_output=$(git -C "$target_path" status --porcelain)
  local cleanup_target_status_exit=$?
  if [[ $cleanup_target_status_exit -ne 0 ]]; then
    echo "failed to inspect target worktree status after merge; cleanup stopped" >&2
    return $cleanup_target_status_exit
  fi
  if [[ -n "$cleanup_target_status_output" ]]; then
    echo "target worktree changed after merge; cleanup stopped" >&2
    return 1
  fi

  local cleanup_source_worktree_branch
  cleanup_source_worktree_branch=$(git -C "$source_path" symbolic-ref --quiet --short HEAD 2>/dev/null)
  if [[ "$cleanup_source_worktree_branch" != "$source_branch" ]]; then
    echo "source worktree branch changed after merge; cleanup stopped" >&2
    return 1
  fi

  local cleanup_source_worktree_head
  cleanup_source_worktree_head=$(git -C "$source_path" rev-parse --verify "HEAD^{commit}" 2>/dev/null)
  if [[ "$cleanup_source_worktree_head" != "$source_head" ]]; then
    echo "source worktree HEAD changed after merge; cleanup stopped" >&2
    return 1
  fi

  local cleanup_source_status_output
  cleanup_source_status_output=$(git -C "$source_path" status --porcelain)
  local cleanup_source_status_exit=$?
  if [[ $cleanup_source_status_exit -ne 0 ]]; then
    echo "failed to inspect source worktree status after merge; cleanup stopped" >&2
    return $cleanup_source_status_exit
  fi
  if [[ -n "$cleanup_source_status_output" ]]; then
    echo "source worktree changed after merge; cleanup stopped" >&2
    return 1
  fi

  local cleanup_source_branch_head
  cleanup_source_branch_head=$(git rev-parse --verify "refs/heads/${source_branch}^{commit}" 2>/dev/null)
  if [[ "$cleanup_source_branch_head" != "$source_head" ]]; then
    echo "source branch changed after merge; cleanup stopped" >&2
    return 1
  fi
  if ! git -C "$target_path" merge-base --is-ancestor "$source_head" HEAD; then
    echo "merged source commit is not an ancestor of target HEAD; cleanup stopped" >&2
    return 1
  fi

  builtin cd -q "$target_path" || return $?
  git worktree remove -- "$source_path" || return $?
  git branch -d -- "$source_branch"
}
