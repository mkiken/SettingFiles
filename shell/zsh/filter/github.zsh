#!/bin/zsh

# ブランチを指定してGitHubのcompare urlを開く
function fgh_compare_url(){
  local base=`br_fmt`
	if test $? -ne 0
	then
		return $EXIT_CODE_SIGINT
	fi
  local compare=`br_fmt`
	if test $? -ne 0
	then
		return $EXIT_CODE_SIGINT
	fi

  gh_compare_url $base $compare
}

# マージ先のブランチ名を表示するPR一覧
function fghpl_branch() {
 ghpl_branch \
    | filter --height 40% --layout reverse --info inline --border \
        --header $'Number\tTitle\tAuthor\tBase\tHead' \
        --delimiter $'\t' --with-nth 1,2,3,4,5
}

# GitHubのPR一覧からブランチ間差分表示（共通祖先からの差分）
function fgd_pr() {
  # GitHubのプルリクエスト一覧をTSV形式で取得
  selected_pr=$(fghpl_branch)

  # PRが選択された場合
  if [ -z "$selected_pr" ]; then
    return $EXIT_CODE_SIGINT
  fi

  # 変数に分解
  IFS=$'\t' read pr_number title author base_ref head_ref <<< "$selected_pr"

  # リモートブランチをフェッチ
  git fetch origin "${base_ref}" "${head_ref}"

  # 差分を表示
  save_history git diff "$@" "origin/${base_ref}...origin/${head_ref}"
}

# GitHubのPR一覧からブランチ間ログ表示（共通祖先からの差分）
function fgl_pr() {
  # GitHubのプルリクエスト一覧をTSV形式で取得
  selected_pr=$(fghpl_branch)

  # PRが選択された場合
  if [ -z "$selected_pr" ]; then

    return $EXIT_CODE_SIGINT
  fi

  # 変数に分解
  IFS=$'\t' read pr_number title author base_ref head_ref <<< "$selected_pr"

  # リモートブランチをフェッチ
  git fetch origin "${base_ref}" "${head_ref}"

  # ログを表示
  save_history git log "$@" "origin/${base_ref}..origin/${head_ref}"
}

# github cli
# マージ先ブランチを選んでPRを作成
function fghpc() {
  local branch=$(br_fmt)
  if [[ -z $branch ]]; then
    return $EXIT_CODE_SIGINT
  fi
  gh pr create --web --body="" --base "$branch" "$@"
}

function fghpch() {
  local branch=$(_fgbh)
  if [[ -z $branch ]]; then
    return $EXIT_CODE_SIGINT
  fi
  gh pr create --web --body="" --base "$branch" "$@"
}

# PR一覧からブラウザで開く
function fghpv(){
  local pr_number=$(ghpl | filter | awk '{print $1}')
  if [[ -n "$pr_number" ]]; then
    no_notify ghpv "$pr_number"
  fi
}

# コミットハッシュからPR検索してブラウザで開く
function fghpv_from_commit(){
  local commit_hash="${1}"
  if [[ -z $commit_hash ]]; then
    echo "Usage: fghpv_from_commit <commit-hash>"
    return $EXIT_CODE_SIGINT
  fi
  local pr_number=$(ghpl_from_commit "$commit_hash" | filter | awk '{print $1}')
  if [[ -n "$pr_number" ]]; then
    no_notify ghpv "$pr_number"
  fi
}

# 自分のPR一覧からブラウザで開く
function fghpvm(){
  local pr_number=$(ghplm | filter | awk '{print $1}')
  if [[ -n "$pr_number" ]]; then
    no_notify ghpv "$pr_number"
  fi
}

# PR一覧からチェックアウト
function fghco(){
  local pr_number=$(ghpl | filter | awk '{print $1}')
  if [[ -n "$pr_number" ]]; then
    no_notify gh co "$pr_number"
  fi
}

# 自分のPR一覧からチェックアウト
function fghcom(){
  local pr_number=$(ghplm | filter | awk '{print $1}')
  if [[ -n "$pr_number" ]]; then
    no_notify gh co "$pr_number"
  fi
}

# 2ブランチを指定してGitHubのPR作成urlを開く
function fghpc2(){
  local base
  base=$(FZF_DEFAULT_OPTS="--prompt='base: ' --header='マージ先ブランチを選択'" br_fmt)
  local ret=$?
  if [[ $ret -ne 0 || -z $base ]]; then
    return $EXIT_CODE_SIGINT
  fi

  local compare
  compare=$(FZF_DEFAULT_OPTS="--prompt='compare: ' --header='マージブランチを選択'" br_fmt)
  ret=$?
  if [[ $ret -ne 0 || -z $compare ]]; then
    return $EXIT_CODE_SIGINT
  fi

  ghpc --base $base --head $compare
}