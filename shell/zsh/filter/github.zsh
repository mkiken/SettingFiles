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

# git logのレンジ指定（A..B）でコミットを絞ってfilterで1つ選び、ハッシュを返す
# _select_commit_hashはブランチ引数を`git rev-parse --verify`で検証するが、
# --verifyは単一revision専用でA..B形式が必ず失敗するため、レンジ用にここを分けている
# 検証は`git log`自体の終了ステータスで兼ねる（不正なレンジならgit logが失敗する）
# 戻り値: 選択されたコミットハッシュ、キャンセル/候補ゼロ時は $EXIT_CODE_SIGINT
function _select_commit_hash_in_range() {
  local header_message="$1"
  local range="$2"
  local limit="${3:-200}"

  local commits
  commits=$(git log --pretty=format:"%C(yellow)%h%C(reset) %C(blue)%an%C(reset) %C(green)%ad%C(reset) %s" \
    --date=short -"$limit" --color=always "$range" 2>/dev/null)
  if [[ $? -ne 0 ]] || [[ -z "$commits" ]]; then
    echo "コミットが見つかりませんでした: ${range}" >&2
    return $EXIT_CODE_SIGINT
  fi

  local selected_commit
  selected_commit=$(echo "$commits" | \
    filter \
      --ansi \
      --layout=reverse \
      --header "$header_message" \
      --prompt "commit> " \
      --preview 'git show --color=always {1}' \
      --preview-window=right:60%:wrap
  )

  if [[ -z "$selected_commit" ]]; then
    return $EXIT_CODE_SIGINT
  fi

  _extract_commit_hash "$selected_commit"
}

# ブランチとコミットをfilterで選び、GitHubのcompare urlをブラウザで開く
# 選択は3段: ブランチ -> base コミット -> compare コミット
# compare候補は「同じブランチかつbaseより後」のコミットのみ（git logのA..Bレンジで絞る）
# 異ブランチ間の比較はfgh_compare_url（ブランチ同士の比較）を使う
function fgh-compare() {
  if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "エラー: 現在のディレクトリはgitリポジトリではありません" >&2
    return 1
  fi

  local branch
  branch=$(br_org)
  if [[ $? -ne 0 ]] || [[ -z "$branch" ]]; then
    return $EXIT_CODE_SIGINT
  fi

  local base_hash
  base_hash=$(_select_commit_hash "compare元(base)のコミットを選択してください" 200 "$branch")
  local base_status=$?
  if [[ $base_status -ne 0 ]] || [[ -z "$base_hash" ]]; then
    return $EXIT_CODE_SIGINT
  fi

  # baseは A..B レンジに含まれないため、compare == base の無意味な比較は候補から自然に外れる
  local compare_hash
  compare_hash=$(_select_commit_hash_in_range "compare先のコミットを選択してください" "${base_hash}..${branch}" 200)
  local compare_status=$?
  if [[ $compare_status -ne 0 ]] || [[ -z "$compare_hash" ]]; then
    return $EXIT_CODE_SIGINT
  fi

  local url
  url=$(_gh_compare_url_build "$base_hash" "$compare_hash") || return $?

  save_history open "$url"
}
alias fghcmp='fgh-compare'

# マージ先のブランチ名を表示するPR一覧
# 先頭の --label-prefix <文字列> はここで剥がしてfilterのpromptへ渡し、
# 残りの引数はghpl_branch（gh pr listのクエリフラグ）へそのまま転送する
function _fgh_select_pr() {
  local label_prefix=""
  if [[ "${1:-}" == "--label-prefix" ]]; then
    label_prefix="$2"
    shift 2
  fi

  local -a filter_args=(--height 40% --layout reverse --info inline --border
    --header $'Number\tTitle\tAuthor\tBase\tHead'
    --delimiter $'\t' --with-nth 1,2,3,4,5)
  [[ -n "$label_prefix" ]] && filter_args+=(--prompt "${label_prefix} ")

  ghpl_branch "$@" | filter "${filter_args[@]}"
}

function _fgh_select_pr_number() {
  local -a label_args=()
  if [[ "${1:-}" == "--label-prefix" ]]; then
    label_args=(--label-prefix "$2")
    shift 2
  fi

  local selected_pr
  selected_pr=$(_fgh_select_pr "${label_args[@]}" "$@")
  if [[ -z "$selected_pr" ]]; then
    return $EXIT_CODE_SIGINT
  fi

  print -r -- "${selected_pr%%$'\t'*}"
}

function fghpl_branch() {
  _fgh_select_pr "$@"
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
function _fghpv_impl(){
  local pr_number=$(_fgh_select_pr_number)
  if [[ -z "$pr_number" ]]; then
    return $EXIT_CODE_SIGINT
  fi
  ghpv "$pr_number"
}
alias fghpv='no_notify _fghpv_impl'

# コミットハッシュからPR検索してブラウザで開く
function _fghpv_from_commit_impl(){
  local commit_hash="${1}"
  if [[ -z $commit_hash ]]; then
    echo "Usage: fghpv_from_commit <commit-hash>"
    return $EXIT_CODE_SIGINT
  fi
  local pr_number=$(_fgh_select_pr_number --search "$commit_hash" --state all)
  if [[ -z "$pr_number" ]]; then
    return $EXIT_CODE_SIGINT
  fi
  ghpv "$pr_number"
}
alias fghpv_from_commit='no_notify _fghpv_from_commit_impl'

# 自分のPR一覧からブラウザで開く
function _fghpvm_impl(){
  local pr_number=$(_fgh_select_pr_number --author "@me")
  if [[ -z "$pr_number" ]]; then
    return $EXIT_CODE_SIGINT
  fi
  ghpv "$pr_number"
}
alias fghpvm='no_notify _fghpvm_impl'

# PR一覧からチェックアウト
function _fghco_impl(){
  local pr_number=$(_fgh_select_pr_number)
  if [[ -z "$pr_number" ]]; then
    return $EXIT_CODE_SIGINT
  fi
  gh co "$pr_number"
}
alias fghco='no_notify _fghco_impl'

# 自分のPR一覧からチェックアウト
function _fghcom_impl(){
  local pr_number=$(_fgh_select_pr_number --author "@me")
  if [[ -z "$pr_number" ]]; then
    return $EXIT_CODE_SIGINT
  fi
  gh co "$pr_number"
}
alias fghcom='no_notify _fghcom_impl'

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
