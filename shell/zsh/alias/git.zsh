#!/bin/zsh
# Git aliases

alias cdgr='cd `g repository`'
alias g='noglob git'
alias ga='git add'
alias gaa='ga .'
alias gb='git branch'
alias gbD='gb -D'
alias gba='gb -a'
alias gbd='gb -d'
alias gca='gci --amend'
alias gcb='git current-branch'
alias gcbc='gcb | tr -d "\n" | pc;echo'
alias gcf='g conflicts'
alias gci='git ci'
alias gcl='g cl'
alias gcln='gcl -n'
alias gcm='gci -m'
alias gco='git co'
alias gcoo='gco --ours'
alias gcot='gco --theirs'
alias gcp='g cp'
alias gd='git diff'
alias gdc='gd --cached'
alias gdn='gd --name-status'
alias gfp='git fetch --all --prune'
alias gl='git log'
alias gln='gl --name-status'
alias glst='gl --stat'
alias glp='gl -p'
# git log for code copy
alias glpc='git -c delta.side-by-side=false -c delta.line-numbers=false log -p'
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
alias gmt='g mt'
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

  # ローカルブランチ（現在のブランチは除外）
  local local_branches=( $(git branch | grep -v '*' -p) )  # リモートブランチ（「origin/HEAD -> origin/master」の行を除外し、「origin/」を消す）
  local remote_branches=( $(git branch -r | grep -v '\->' -p | sed -e 's/origin\///') )
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

    # リモートになかったら確認プロンプトを出す
    if [[ ${is_in_remote} = false ]]; then
      echo "branch '${local_branch}' is not in remote. delete it? [y/N]"

      read -r ANSWER

      # 「Y」、「y」などであれば削除
      case ${ANSWER} in
        "Y" | "y" | "yes" | "Yes" | "YES" ) git branch -D "${local_branch}";;
        * ) echo "not delete branch '${local_branch}'.";;
      esac
    fi
  done
}

# difit
difit() {
  npx difit "$@"
}
di() {
  difit "$@"
}
alias diw='di working'
alias dis='di staged'