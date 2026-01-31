#!/bin/zsh

# gitブランチのプレビューコマンドを生成する共通関数
function _git_branch_preview_command() {
  echo "echo {} | sed -e 's/[*+]//' | awk '{print \$1}' \
    | xargs git log --color --graph --decorate --abbrev-commit \
      --format=format:'%C(blue)%h%C(reset) - %C(green)(%ar)%C(reset)%C(yellow)%d%C(reset)\n  %C(white)%s%C(reset) %C(dim white)- %an%C(reset)'"
}


alias fgmg='filter_git_command git merge'
alias fgmgs='fgmg --squash'
alias fgpl='filter_git_command_fmt git pull origin'
alias fgps='filter_git_command_fmt git push origin'
alias fgbd='filter_git_command_local git branch -d'
alias fgbD='filter_git_command_local git branch -D'
alias fgb='br_org'
alias fgbd-remote='filter_git_command_remote git push --delete --no-verify origin'
alias fgrb='filter_git_command_fmt git pull --rebase origin'
alias fgl='filter_git_command git log'
alias fgln='fgl --name-status'
alias fglp='fgl -p'
alias fgd='filter_git_command git diff'
alias fgdn='fgd --name-status'
alias fgls='fgl --stat'

alias fgcf='gcf | filter'
alias fgmt='gmt "$(fgcf)"'
alias fgcfa='ga "$(fgcf)"'
alias fgcoo='gcoo "$(fgcf)"'
alias fgcot='gcot "$(fgcf)"'

# gitコミット一覧を取得する共通関数
# 引数: limit (デフォルト: 30), branch (オプショナル)
function _get_git_commits() {
  local limit=${1:-30}
  local branch=${2:-}

  # ブランチが指定されている場合はブランチの存在確認
  if [[ -n "$branch" ]]; then
    if ! git rev-parse --verify "$branch" >/dev/null 2>&1; then
      echo "エラー: ブランチ '$branch' が見つかりません" >&2
      return 1
    fi
    git log --pretty=format:"%C(yellow)%h%C(reset) %C(blue)%an%C(reset) %C(green)%ad%C(reset) %s" --date=short -"$limit" --color=always "$branch" 2>/dev/null
  else
    git log --pretty=format:"%C(yellow)%h%C(reset) %C(blue)%an%C(reset) %C(green)%ad%C(reset) %s" --date=short -"$limit" --color=always 2>/dev/null
  fi
}

# フィルター選択されたコミットからハッシュを抽出する共通関数
# 引数: selected_commit (フィルター結果の文字列)
function _extract_commit_hash() {
  local selected_commit="$1"
  if [[ -z "$selected_commit" ]]; then
    return 1
  fi
  echo "$selected_commit" | awk '{print $1}' | sed 's/\x1b\[[0-9;]*m//g'
}

# コミット選択UI全体の統合関数
# 引数1: header_message (フィルターのヘッダーメッセージ)
# 引数2: limit (コミット数の上限、デフォルト: 30)
# 引数3: branch (オプショナル: 特定のブランチのコミットを取得)
# 戻り値: 選択されたコミットハッシュ（標準出力）、キャンセル時は $EXIT_CODE_SIGINT で終了
function _select_commit_hash() {
  local header_message="$1"
  local limit="${2:-30}"
  local branch="${3:-}"

  # コミット取得と検証
  local commits
  commits=$(_get_git_commits "$limit" "$branch")
  if [[ $? -ne 0 ]] || [[ -z $commits ]]; then
    echo "コミットが見つかりませんでした" >&2
    return $EXIT_CODE_SIGINT
  fi

  # フィルターでコミット選択
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

  # ユーザーキャンセル時の適切な終了処理
  if [[ -z $selected_commit ]]; then
    return $EXIT_CODE_SIGINT
  fi

  # 選択されたコミットハッシュを抽出
  local commit_hash
  commit_hash=$(_extract_commit_hash "$selected_commit")

  if [[ -z $commit_hash ]]; then
    echo "エラー: コミットハッシュの抽出に失敗しました" >&2
    return 1
  fi

  echo "$commit_hash"
}

function _fgbh(){
  local branches=$(git --no-pager reflog \
    | awk '$3 == "checkout:" && /moving from/ {print $8}' \
    | awk '!seen[$0]++' \
    | grep -Fx -f <(git branch --format='%(refname:short)') \
    | head -30)
  if [[ -z $branches ]]; then
    echo "最近移動したブランチが見つかりませんでした"
    return $EXIT_CODE_SIGINT
  fi
  echo "$branches" \
    | filter --preview "$(_git_branch_preview_command)"
}

# 直近移動したブランチ一覧からgit switchする
function fgbh(){
  local temp=`_fgbh | xargs echo`
  if [[ -n $temp ]]
  then
    save_history git switch $temp
  else
    return $EXIT_CODE_SIGINT
  fi
}

# git switch by branch filter
function fgsw(){
  local temp=`br_fmt | xargs echo`
  if [[ -z $temp ]]; then
    return $EXIT_CODE_SIGINT
  fi
  save_history git sw "$@" "$temp"
}

# git switch -c by branch filter
function fgswc(){
  local temp=`br_org | xargs echo`
  if [[ -z $temp ]]; then
    return $EXIT_CODE_SIGINT
  fi
  save_history gswc "$@" "$temp"
}

# Gitのブランチをfilter toolで扱えるように整形(remote文字列を削る)
function br_fmt(){
  br_org | sed -e 's/remotes\/origin\///'
}

# Gitのブランチをfilter toolで扱えるように整形
function br_org(){
  # 取り込まれたコミットのタイムスタンプを降順(-)でソート
  # ログをいい感じに表示 https://zenn.dev/yamo/articles/5c90852c9c64ab
  git branch -a --sort=-committerdate --color | grep -v "\->" \
    | filter --preview "$(_git_branch_preview_command)" \
    | xargs echo | _clean_git_branch_markers | awk '{print $1}'
}

# Gitのローカルブランチのみをfilter toolで扱えるように整形
function br_local(){
  # 取り込まれたコミットのタイムスタンプを降順(-)でソート
  git branch --sort=-committerdate --color | grep -v "\->" \
    | filter --preview "$(_git_branch_preview_command)" \
    | xargs echo | _clean_git_branch_markers | awk '{print $1}'
}

# Gitのブランチをfilter toolで扱えるように整形
function br_remote(){
  # 取り込まれたコミットのタイムスタンプを降順（-）でソート
  # ログをいい感じに表示 https://zenn.dev/yamo/articles/5c90852c9c64ab
  git branch -r --sort=-committerdate --color \
    | grep -v "\->" | sed -e 's/origin\///' \
    | filter --preview "$(_git_branch_preview_command)" \
    | xargs echo | _clean_git_branch_markers | awk '{print $1}'
}

# br_fmtのリモート対象版
function br_fmt_remote(){
  br_fmt | xargs echo | awk '{printf("%s%s\n", "remotes/origin/", $0)}'
}

# ブランチをfilter toolで絞ってgitコマンドを実行する
function filter_git_command(){
  local branch
  if branch=$(br_org); then
    save_history "$@" "$branch"
  else
    return $?
  fi
}

function filter_git_command_fmt(){
  local branch
  if branch=$(br_fmt); then
    save_history "$@" "$branch"
  else
    return $?
  fi
}

function filter_git_command_remote(){
  local branch
  if branch=$(br_remote); then
    save_history "$@" "$branch"
  else
    return $?
  fi
}

function filter_git_command_local(){
  local branch
  if branch=$(br_local); then
    save_history "$@" "$branch"
  else
    return $?
  fi
}

# 指定したリファレンス（ブランチやハッシュ）からファイル/ディレクトリをfilterで選択
# $1: 比較元（ブランチ名やハッシュ）
# $2: 比較先（現在のブランチ名など）
function filter_git_file_or_dir() {
  local ref="$1"
  local compare_ref="$2"
  {
    git ls-tree -r --name-only "$compare_ref"
    git ls-tree -r --name-only "$compare_ref" | grep -o '^.*/' | sort -u
  } | sort -u | filter --prompt="file/dir: " --header="ファイルまたはディレクトリを選択" \
    --preview="git diff --color=always $ref..$compare_ref -- {}"
}

# filter git diff for file
function fgd-branch-file(){
  # ブランチ選択
  local branch=$(FZF_DEFAULT_OPTS="--prompt='branch: ' --header='比較ブランチを選択'" br_fmt)
  if [[ -z $branch ]]; then
    echo "ブランチが選択されていません"
    return $EXIT_CODE_SIGINT
  fi

  # ファイル＋ディレクトリ一覧を直接パイプでfilterに渡す
  local target=$(filter_git_file_or_dir "$branch" "$(git rev-parse --abbrev-ref HEAD)")
  if [[ -z $target ]]; then
    echo "ファイルまたはディレクトリが選択されていません"
    return $EXIT_CODE_SIGINT
  fi

  # diff実行
  save_history git diff "$branch" -- "$target"
}

# コミットハッシュを指定して、ファイルやディレクトリをfilterで選んでdiffを表示
function fgd-hash-file() {
  local hash="$1"
  if [[ -z $hash ]]; then
    echo "コミットハッシュを引数で指定してください 例: fgd-hash-file <commit-hash>"
    return $EXIT_CODE_SIGINT
  fi

  # ファイル＋ディレクトリ一覧をfilterで選択
  local target=$(filter_git_file_or_dir "$hash" "$(git rev-parse --abbrev-ref HEAD)")
  if [[ -z $target ]]; then
    echo "ファイルまたはディレクトリが選択されていません"
    return $EXIT_CODE_SIGINT
  fi

  # diff実行
  save_history git diff "$hash" -- "$target"
}

# filter git checkout for file
function fgco-branch-file(){
  # ブランチ選択
  local branch=$(FZF_DEFAULT_OPTS="--prompt='branch: ' --header='比較ブランチを選択'" br_fmt)
  if [[ -z $branch ]]; then
    echo "ブランチが選択されていません"
    return $EXIT_CODE_SIGINT
  fi

  # ファイル＋ディレクトリ一覧を直接パイプでfilterに渡す
  local target=$(filter_git_file_or_dir "$(git rev-parse --abbrev-ref HEAD)" "$branch")
  if [[ -z $target ]]; then
    echo "ファイルまたはディレクトリが選択されていません"
    return $EXIT_CODE_SIGINT
  fi

  # diff実行
  save_history git co "$branch" -- "$target"
}

# コミットハッシュを指定して、ファイルやディレクトリをfilterで選んでcheckoutを実行
function fgco-hash-file() {
  local hash="$1"
  if [[ -z $hash ]]; then
    echo "コミットハッシュを引数で指定してください 例: fgco-hash-file <commit-hash>"
    return $EXIT_CODE_SIGINT
  fi

  # ファイル＋ディレクトリ一覧をfilterで選択
  local target=$(filter_git_file_or_dir "$(git rev-parse --abbrev-ref HEAD)" "$hash")
  if [[ -z $target ]]; then
    echo "ファイルまたはディレクトリが選択されていません"
    return $EXIT_CODE_SIGINT
  fi

  # diff実行
  save_history git co "$hash" -- "$target"
}

# filter git show for file
function fgs-branch-file(){
  # ブランチ選択
  local branch=$(FZF_DEFAULT_OPTS="--prompt='branch: ' --header='比較ブランチを選択'" br_org)
  if [[ -z $branch ]]; then
    echo "ブランチが選択されていません"
    return $EXIT_CODE_SIGINT
  fi

  # ファイル＋ディレクトリ一覧を直接パイプでfilterに渡す
  local target=$(filter_git_file_or_dir "$(git rev-parse --abbrev-ref HEAD)" "$branch")
  if [[ -z $target ]]; then
    echo "ファイルまたはディレクトリが選択されていません"
    return $EXIT_CODE_SIGINT
  fi

  save_history git show "${branch}":"$target"
}

function fgs-hash-file() {
  local hash="$1"
  if [[ -z $hash ]]; then
    echo "コミットハッシュを引数で指定してください 例: fgs-hash-file <commit-hash>"
    return $EXIT_CODE_SIGINT
  fi

  # ファイル＋ディレクトリ一覧をfilterで選択
  local target=$(filter_git_file_or_dir "$(git rev-parse --abbrev-ref HEAD)" "$hash")
  if [[ -z $target ]]; then
    echo "ファイルまたはディレクトリが選択されていません"
    return $EXIT_CODE_SIGINT
  fi

  save_history git show "${hash}":"$target"
}

# git管理されているファイル・ディレクトリ一覧をfilterで選択する汎用関数
function _filter_git_managed_files() {
  {
    # git管理下の全ファイルを取得
    git ls-files

    # ディレクトリも追加（重複を排除）
    git ls-files | grep -o "^.*/" | sort -u
  } | sort -u | filter \
    --prompt="file/dir: " \
    --header="git管理されているファイルまたはディレクトリを選択" \
    --preview='
      if [[ -d {1} ]]; then
        echo "ディレクトリ: {1}"
        echo "----"
        git log --oneline --color=always -10 -- {1}
      else
        echo "ファイル: {1}"
        echo "----"
        git log --oneline --color=always -10 -- {1}
      fi
    '
}

# 選択したファイル・ディレクトリの履歴からコミットハッシュを選択する関数
function _select_commit_hash_for_file() {
  local file_path="$1"
  local header_message="$2"
  local limit="${3:-30}"

  # ファイル・ディレクトリの履歴を取得（最新コミットを除外）
  local commits
  commits=$(git log --pretty=format:"%C(yellow)%h%C(reset) %C(blue)%an%C(reset) %C(green)%ad%C(reset) %s" --date=short -"$limit" --color=always --skip=1 -- "$file_path" 2>/dev/null)

  if [[ $? -ne 0 ]] || [[ -z $commits ]]; then
    echo "ファイル '$file_path' の履歴が見つかりませんでした（最新コミット以外）" >&2
    return $EXIT_CODE_SIGINT
  fi

  # フィルターでコミット選択
  local selected_commit
  selected_commit=$(echo "$commits" | \
    filter \
      --ansi \
      --layout=reverse \
      --header "$header_message" \
      --prompt "commit> " \
      --preview "git diff --color=always HEAD..{1} -- '$file_path'" \
      --preview-window=right:60%:wrap
  )

  # ユーザーキャンセル時の適切な終了処理
  if [[ -z $selected_commit ]]; then
    return $EXIT_CODE_SIGINT
  fi

  # 選択されたコミットハッシュを抽出
  local commit_hash
  commit_hash=$(_extract_commit_hash "$selected_commit")

  if [[ -z $commit_hash ]]; then
    echo "エラー: コミットハッシュの抽出に失敗しました" >&2
    return 1
  fi

  echo "$commit_hash"
}

# git管理されているファイル・ディレクトリから履歴を選んでcheckoutする
function fgco-file() {
  # gitリポジトリ検証
  if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "エラー: 現在のディレクトリはgitリポジトリではありません"
    return 1
  fi

  # ファイル・ディレクトリ選択
  local target_file
  target_file=$(_filter_git_managed_files)
  if [[ -z $target_file ]]; then
    echo "ファイルまたはディレクトリが選択されていません"
    return $EXIT_CODE_SIGINT
  fi

  # コミット選択
  local commit_hash
  commit_hash=$(_select_commit_hash_for_file "$target_file" "ファイル '$target_file' をcheckoutするコミットを選択してください" 30)

  # キャンセルまたはエラー時は適切な終了処理
  if [[ $? -ne 0 ]]; then
    return $?
  fi

  # git checkout実行
  echo "ファイル '$target_file' を $commit_hash の状態にcheckoutしています..."
  save_history git checkout "$commit_hash" -- "$target_file"
}

# GitHubのPRのようなブランチ間差分表示（共通祖先からの差分）
function fgd2(){
  local base
  base=$(FZF_DEFAULT_OPTS="--prompt='base: ' --header='比較元ブランチを選択'" br_org)
  local ret=$?
  if [[ $ret -ne 0 || -z $base ]]; then
    return $EXIT_CODE_SIGINT
  fi
  local compare
  compare=$(FZF_DEFAULT_OPTS="--prompt='compare: ' --header='比較先ブランチを選択'" br_org)
  ret=$?
  if [[ $ret -ne 0 || -z $compare ]]; then
    return $EXIT_CODE_SIGINT
  fi
  save_history git diff "$@" $base...$compare
}

# GitHubのPRのようなブランチ間ログ表示（共通祖先からの差分）
function fgl2(){
  local base
  base=$(FZF_DEFAULT_OPTS="--prompt='base: ' --header='比較元ブランチを選択'" br_org)
  local ret=$?
  if [[ $ret -ne 0 || -z $base ]]; then
    return $EXIT_CODE_SIGINT
  fi
  local compare
  compare=$(FZF_DEFAULT_OPTS="--prompt='compare: ' --header='比較先ブランチを選択'" br_org)
  ret=$?
  if [[ $ret -ne 0 || -z $compare ]]; then
    return $EXIT_CODE_SIGINT
  fi
  save_history git log "$@" $base..$compare
}

# Git管理下の変更ファイル・ディレクトリをfilterで選択する汎用関数
function filter_git_changed_files() {
  {
    # 変更のあるファイルを取得
    git ls-files --modified --others --exclude-standard

    # ディレクトリも追加（重複を排除）
    git ls-files --modified --others --exclude-standard |
      grep -o "^.*/" |
      sort -u
  } |
  filter --preview '
    if [[ -d {1} ]]; then
      # ディレクトリの場合はそのディレクトリ内の変更ファイル一覧を表示
      git diff --name-status -- {1}
    else
      # ファイルの場合はdiffを表示
      git diff --color=always -- {1}
    fi
  '
}

# 差分のあるファイルを選択してdiffを表示
function fgds() {
  local selection=$(filter_git_changed_files)

  # 選択されたものがなければ早期リターン
  if [ -z "$selection" ]; then
      return $EXIT_CODE_SIGINT
  fi
  save_history git diff --color=always -- "$selection" | less -R
}

# 選択したファイル・ディレクトリをstashする
function fgst(){
  local selection=$(filter_git_changed_files)

  # 選択されたものがなければ早期リターン
  if [ -z "$selection" ]; then
      return $EXIT_CODE_SIGINT
  fi

  local stash_message="${selection}"
  save_history git stash push -m "$stash_message" -- "$selection"
  echo "Stashed selected files with message: $stash_message"
}

# 選択したファイル・ディレクトリをaddする
function fga(){
  local selection=$(filter_git_changed_files)

  # 選択されたものがなければ早期リターン
  if [ -z "$selection" ]; then
      return $EXIT_CODE_SIGINT
  fi

  save_history git add "$selection"
}

function fghq() {
  local src=$(ghq list | filter --preview "bat --color=always --style=header,grid --line-range :80 $(ghq root)/{}/README.*")
  if [ -z "$src" ]; then
    return $EXIT_CODE_SIGINT
  fi
  save_history cd "$(ghq root)/$src"
}

# [difit と fzf を合わせてみた](https://zenn.dev/whatasoda/articles/6e7b921bfbc968)
fdifit() {
  local from_commit to_commit from_hash to_hash

  from_commit=$(git log --oneline --decorate -100 --color=always | \
    filter \
      --ansi \
      --header "> difit \$TO \$FROM~1" \
      --prompt "Select \$FROM>" \
      --preview 'git log --oneline --decorate --color=always -1 {1}' \
      --preview-window=top:3:wrap
  ) || return
  from_hash="${from_commit%% *}"

  to_commit=$(git log --oneline --decorate -100 --color=always $from_hash~1.. | \
    filter \
      --ansi \
      --header "> difit \$TO $from_hash~1" \
      --prompt "Select \$TO>" \
      --preview 'git log --oneline --decorate --color=always -1 {1}' \
      --preview-window=top:3:wrap
  ) || return
  to_hash="${to_commit%% *}"

  difit "$to_hash" "$from_hash~1"
}
alias fdi='fdigit'

# fzfを使用してコミットを選択し、選択されたコミットをrevertする
function fgrv() {
  # gitリポジトリ検証
  if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "エラー: 現在のディレクトリはgitリポジトリではありません"
    return 1
  fi

  # 統合関数を使用してコミットを選択
  local commit_hash
  commit_hash=$(_select_commit_hash "revertするコミットを選択してください" 30)

  # キャンセルまたはエラー時は統合関数の戻り値をそのまま返す
  if [[ $? -ne 0 ]]; then
    return $?
  fi

  # git revert実行（gitのネイティブエラーハンドリングに委ねる）
  echo "コミット $commit_hash をrevertしています..."
  git revert "$commit_hash"

  # git revertの終了コードをそのまま返す
  return $?
}

# fzfを使用してコミットを選択し、選択されたコミットまでrollback（reset --hard）する
function fg-rollback() {
  # gitリポジトリ検証
  if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "エラー: 現在のディレクトリはgitリポジトリではありません"
    return 1
  fi

  # 統合関数を使用してコミットを選択
  local commit_hash
  commit_hash=$(_select_commit_hash "rollback（reset --hard）するコミットを選択してください" 30)

  # キャンセルまたはエラー時は統合関数の戻り値をそのまま返す
  if [[ $? -ne 0 ]]; then
    return $?
  fi

  # 警告メッセージ表示
  echo "⚠️  警告: この操作は作業ディレクトリとステージングエリアの変更を全て破棄し、"
  echo "    コミット $commit_hash の状態に戻します。"
  echo "    この操作は取り消しできません。"
  echo -n "本当にrollbackしますか？ (y/N): "
  read -r response

  # 明示的にyまたはYの場合のみ実行
  if [[ "$response" =~ ^[yY]$ ]]; then
    echo "コミット $commit_hash にrollbackしています..."
    git rollback "$commit_hash"
    return $?
  else
    echo "rollbackをキャンセルしました"
    return $EXIT_CODE_SIGINT
  fi
}

# fzfを使用してブランチとコミットを選択し、cherry-pickを実行する
# 既存のbr_org()とenhanced _select_commit_hash()を活用したインタラクティブなcherry-pick
function fgcp() {
  # gitリポジトリ検証
  if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "エラー: 現在のディレクトリはgitリポジトリではありません"
    return 1
  fi

  # ブランチ選択（br_org()関数を活用）
  local selected_branch
  selected_branch=$(br_org)

  # ユーザーキャンセル時または選択失敗時の適切な処理
  if [[ $? -ne 0 ]] || [[ -z "$selected_branch" ]]; then
    return $EXIT_CODE_SIGINT
  fi

  # コミット選択（拡張された_select_commit_hash()にブランチパラメータを渡す）
  local commit_hash
  commit_hash=$(_select_commit_hash "cherry-pickするコミットを選択してください" 30 "$selected_branch")

  # キャンセルまたはエラー時は統合関数の戻り値をそのまま返す
  if [[ $? -ne 0 ]]; then
    return $?
  fi

  # git cherry-pick実行（gitのネイティブエラーハンドリングに委ねる）
  echo "ブランチ '$selected_branch' からコミット $commit_hash をcherry-pickしています..."
  git cherry-pick "$commit_hash"
  local cherry_pick_result=$?

  # コマンド履歴保存（成功・失敗に関わらず履歴に記録）
  save_history git cherry-pick "$commit_hash"

  # 成功時のメッセージ表示
  if [[ $cherry_pick_result -eq 0 ]]; then
    echo "✅ cherry-pickが正常に完了しました"
  fi

  # gitの終了コードをそのまま返す（コンフリクト時はgitの標準処理に委ねる）
  return $cherry_pick_result
}

# workmux listからworktree名をfilterで選択する内部関数
# 戻り値: 選択されたworktree名（ディレクトリ名）、キャンセル時は $EXIT_CODE_SIGINT で終了
function _filter_workmux_worktree() {
  local worktrees
  worktrees=$(wml | tail -n +2 | grep -v '(here)')

  if [[ -z "$worktrees" ]]; then
    echo "選択可能なworktreeがありません" >&2
    return $EXIT_CODE_SIGINT
  fi

  local selected
  selected=$(echo "$worktrees" | filter \
    --header "worktreeを選択" \
    --prompt "worktree> " \
    --preview 'echo {} | awk "{print \$4}" | xargs -I{} git -C {} log --oneline --color=always -10 2>/dev/null || echo "プレビュー取得失敗"'
  )

  if [[ -z "$selected" ]]; then
    return $EXIT_CODE_SIGINT
  fi

  # PATH列（4番目）からディレクトリ名を抽出
  echo "$selected" | awk '{print $4}' | xargs basename
}

# workmux listからworktreeのフルパスをfilterで選択する内部関数
# 戻り値: 選択されたworktreeのフルパス、キャンセル時は $EXIT_CODE_SIGINT で終了
function _filter_workmux_worktree_path() {
  local worktrees
  worktrees=$(wml | tail -n +2 | grep -v '(here)')

  if [[ -z "$worktrees" ]]; then
    echo "選択可能なworktreeがありません" >&2
    return $EXIT_CODE_SIGINT
  fi

  local selected
  selected=$(echo "$worktrees" | filter \
    --header "worktreeを選択" \
    --prompt "worktree> " \
    --preview 'echo {} | awk "{print \$4}" | xargs -I{} git -C {} log --oneline --color=always -10 2>/dev/null || echo "プレビュー取得失敗"'
  )

  if [[ -z "$selected" ]]; then
    return $EXIT_CODE_SIGINT
  fi

  # PATH列（4番目）からフルパスを抽出
  echo "$selected" | awk '{print $4}'
}

# filterでworktreeを選択して現在のpaneでcdする
function fwmo() {
  local worktree_path
  worktree_path=$(_filter_workmux_worktree_path)

  if [[ $? -ne 0 ]] || [[ -z "$worktree_path" ]]; then
    return $EXIT_CODE_SIGINT
  fi

  save_history cd "$worktree_path"
}

# filterでworktreeを選択して新しいウィンドウで開く（workmux open）
function fwmon() {
  local worktree_name
  worktree_name=$(_filter_workmux_worktree)

  if [[ $? -ne 0 ]] || [[ -z "$worktree_name" ]]; then
    return $EXIT_CODE_SIGINT
  fi

  save_history wmo "$worktree_name"
}

# filterでworktreeを選択して水平分割（左右）して新しいpaneで開く
function fwmoh() {
  local worktree_path
  worktree_path=$(_filter_workmux_worktree_path)

  if [[ $? -ne 0 ]] || [[ -z "$worktree_path" ]]; then
    return $EXIT_CODE_SIGINT
  fi

  tmux split-window -h -c "$worktree_path"
}

# filterでworktreeを選択して垂直分割（上下）して新しいpaneで開く
function fwmov() {
  local worktree_path
  worktree_path=$(_filter_workmux_worktree_path)

  if [[ $? -ne 0 ]] || [[ -z "$worktree_path" ]]; then
    return $EXIT_CODE_SIGINT
  fi

  tmux split-window -v -c "$worktree_path"
}

# filterでworktreeを選択してworkmux removeを実行
function fwmr() {
  local worktree_name
  worktree_name=$(_filter_workmux_worktree)

  if [[ $? -ne 0 ]] || [[ -z "$worktree_name" ]]; then
    return $EXIT_CODE_SIGINT
  fi

  save_history wmr "$worktree_name"
}