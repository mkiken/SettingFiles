#!/bin/zsh

alias fgmg='filter_git_command git merge'
alias fgmgs='fgmg --squash'
alias fgpl='filter_git_command_fmt git pull origin'
alias fgps='filter_git_command_fmt git push origin'
alias fgbd='filter_git_command_fmt git branch -d'
alias fgbD='filter_git_command_fmt git branch -D'
alias fgb='br_org'
alias fgbd-remote='filter_git_command_fmt git push --delete origin'
alias fgrb='filter_git_command_fmt git pull --rebase origin'
alias fgl='filter_git_command git log'
alias fgln='fgl --name-status'
alias fglp='fgl -p'
alias fgd='filter_git_command git diff'
alias fgdn='fgd --name-status'
alias fgls='fgl --stat'

alias fgcf='gcf | filter'
alias fgmt='gmt $(fgcf)'
alias fgcfa='ga $(fgcf)'
alias fgcoo='gcoo $(fgcf)'
alias fgcot='gcot $(fgcf)'

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
    | filter --preview "echo {} | sed -e 's/\*//' | awk '{print \$1}' \
      | xargs git log --color --graph --decorate --abbrev-commit \
        --format=format:'%C(blue)%h%C(reset) - %C(green)(%ar)%C(reset)%C(yellow)%d%C(reset)\n  %C(white)%s%C(reset) %C(dim white)- %an%C(reset)'"
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
  # 取り込まれたコミットのタイムスタンプを降順（-）でソート
  # ログをいい感じに表示 https://zenn.dev/yamo/articles/5c90852c9c64ab
  git branch -a --sort=-committerdate --color \
    | filter --preview "echo {} | sed -e 's/\*//' | awk '{print \$1}' \
      | xargs git log --color --graph --decorate --abbrev-commit \
        --format=format:'%C(blue)%h%C(reset) - %C(green)(%ar)%C(reset)%C(yellow)%d%C(reset)\n  %C(white)%s%C(reset) %C(dim white)- %an%C(reset)'" \
    | xargs echo | sed -e 's/\*//' | awk '{print $1}'
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

# 指定したリファレンス（ブランチやハッシュ）からファイル/ディレクトリをfilterで選択
# $1: 比較元（ブランチ名やハッシュ）
# $2: 比較先（現在のブランチ名など）
function filter_git_file_or_dir() {
  local ref="$1"
  local compare_ref="$2"
  {
    git ls-tree -r --name-only "$ref"
    git ls-tree -r --name-only "$ref" | grep -o '^.*/' | sort -u
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
  local target=$(filter_git_file_or_dir "$branch" "$(git rev-parse --abbrev-ref HEAD)")
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
  local target=$(filter_git_file_or_dir "$hash" "$(git rev-parse --abbrev-ref HEAD)")
  if [[ -z $target ]]; then
    echo "ファイルまたはディレクトリが選択されていません"
    return $EXIT_CODE_SIGINT
  fi

  save_history git show "${hash}":"$target"
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

# Git管理下の変更ファイル・ディレクトリをfzfで選択する汎用関数
function filter_git_changed_files() {
  {
    # 変更のあるファイルを取得
    git ls-files --modified --others --exclude-standard

    # ディレクトリも追加（重複を排除）
    git ls-files --modified --others --exclude-standard |
      grep -o "^.*/" |
      sort -u
  } |
  fzf --preview '
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
  git diff --color=always -- "$selection" | less -R
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
  save_history git stash push -m "$stash_message" -- $selection
  echo "Stashed selected files with message: $stash_message"
}

# 選択したファイル・ディレクトリをaddする
function fga(){
  local selection=$(filter_git_changed_files)

  # 選択されたものがなければ早期リターン
  if [ -z "$selection" ]; then
      return $EXIT_CODE_SIGINT
  fi

  save_history git add $selection
}

function fghq() {
  local src=$(ghq list | fzf --preview "bat --color=always --style=header,grid --line-range :80 $(ghq root)/{}/README.*")
  if [ -z "$src" ]; then
    return $EXIT_CODE_SIGINT
  fi
  cd $(ghq root)/$src
}

# [difit と fzf を合わせてみた](https://zenn.dev/whatasoda/articles/6e7b921bfbc968)
fdifit() {
  local from_commit to_commit from_hash to_hash

  from_commit=$(git log --oneline --decorate -100 --color=always | \
    fzf \
      --ansi \
      --header "> difit \$TO \$FROM~1" \
      --prompt "Select \$FROM>" \
      --preview 'git log --oneline --decorate --color=always -1 {1}' \
      --preview-window=top:3:wrap
  ) || return
  from_hash="${from_commit%% *}"

  to_commit=$(git log --oneline --decorate -100 --color=always $from_hash~1.. | \
    fzf \
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