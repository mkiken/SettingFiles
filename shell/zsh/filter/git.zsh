#!/usr/local/bin/zsh

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
alias fga='ga $(fgcf)'
alias fgcoo='gcoo $(fgcf)'
alias fgcot='gcot $(fgcf)'

function _fgbh(){
  git --no-pager reflog | awk '$3 == "checkout:" && /moving from/ {print $8}' | awk '!seen[$0]++' | grep -Fx -f <(git branch --format='%(refname:short)') | head -30 | filter --preview "echo {} | sed -e 's/\*//' | awk '{print \$1}' | xargs git log --color --graph --decorate --abbrev-commit --format=format:'%C(blue)%h%C(reset) - %C(green)(%ar)%C(reset)%C(yellow)%d%C(reset)\n  %C(white)%s%C(reset) %C(dim white)- %an%C(reset)'"
}

# 直近移動したブランチ一覧からgit switchする
function fgbh(){
  local temp=`_fgbh | xargs echo`
  if [[ -n $temp ]]
  then
    save_history git switch $temp
  else
    return 1
  fi
}

# git switch by branch filter
function fgsw(){
  local temp=`br_fmt | xargs echo`
  if [[ -n $temp ]]
  then
    save_history git sw "$@" "$temp"
  fi
}

# git switch -c by branch filter
function fgswc(){
  local temp=`br_org | xargs echo`
  if [[ -n $temp ]]
  then
    save_history gswc "$@" "$temp"
  fi
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
    | filter --preview "echo {} | sed -e 's/\*//' | awk '{print \$1}' | xargs git log --color --graph --decorate --abbrev-commit --format=format:'%C(blue)%h%C(reset) - %C(green)(%ar)%C(reset)%C(yellow)%d%C(reset)\n  %C(white)%s%C(reset) %C(dim white)- %an%C(reset)'" \
    | xargs echo | sed -e 's/\*//' | awk '{print $1}'
}

# br_fmtのリモート対象版
function br_fmt_remote(){
  br_fmt | xargs echo | awk '{printf("%s%s\n", "remotes/origin/", $0)}'
}

# ブランチをfilter toolで絞ってgitコマンドを実行する
function filter_git_command(){
  local branch=$(br_org)
  save_history "$@" "$branch"
}

function filter_git_command_fmt(){
  local branch=$(br_fmt)
  save_history "$@" "$branch"
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
    return 1
  fi

  # ファイル＋ディレクトリ一覧を直接パイプでfilterに渡す
  local target=$(filter_git_file_or_dir "$branch" "$(git rev-parse --abbrev-ref HEAD)")
  if [[ -z $target ]]; then
    echo "ファイルまたはディレクトリが選択されていません"
    return 1
  fi

  # diff実行
  save_history git diff "$branch" -- "$target"
}

# コミットハッシュを指定して、ファイルやディレクトリをfilterで選んでdiffを表示
function fgd-hash-file() {
  local hash="$1"
  if [[ -z $hash ]]; then
    echo "コミットハッシュを引数で指定してください 例: fgd-hash-file <commit-hash>"
    return 1
  fi

  # ファイル＋ディレクトリ一覧をfilterで選択
  local target=$(filter_git_file_or_dir "$hash" "$(git rev-parse --abbrev-ref HEAD)")
  if [[ -z $target ]]; then
    echo "ファイルまたはディレクトリが選択されていません"
    return 1
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
    return 1
  fi

  # ファイル＋ディレクトリ一覧を直接パイプでfilterに渡す
  local target=$(filter_git_file_or_dir "$(git rev-parse --abbrev-ref HEAD)" "$branch")
  if [[ -z $target ]]; then
    echo "ファイルまたはディレクトリが選択されていません"
    return 1
  fi

  # diff実行
  save_history git co "$branch" -- "$target"
}

# コミットハッシュを指定して、ファイルやディレクトリをfilterで選んでcheckoutを実行
function fgco-hash-file() {
  local hash="$1"
  if [[ -z $hash ]]; then
    echo "コミットハッシュを引数で指定してください 例: fgco-hash-file <commit-hash>"
    return 1
  fi

  # ファイル＋ディレクトリ一覧をfilterで選択
  local target=$(filter_git_file_or_dir "$(git rev-parse --abbrev-ref HEAD)" "$hash")
  if [[ -z $target ]]; then
    echo "ファイルまたはディレクトリが選択されていません"
    return 1
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
    return 1
  fi

  # ファイル＋ディレクトリ一覧を直接パイプでfilterに渡す
  local target=$(filter_git_file_or_dir "$branch" "$(git rev-parse --abbrev-ref HEAD)")
  if [[ -z $target ]]; then
    echo "ファイルまたはディレクトリが選択されていません"
    return 1
  fi

  save_history git show "${branch}":"$target"
}

function fgs-hash-file() {
  local hash="$1"
  if [[ -z $hash ]]; then
    echo "コミットハッシュを引数で指定してください 例: fgs-hash-file <commit-hash>"
    return 1
  fi

  # ファイル＋ディレクトリ一覧をfilterで選択
  local target=$(filter_git_file_or_dir "$hash" "$(git rev-parse --abbrev-ref HEAD)")
  if [[ -z $target ]]; then
    echo "ファイルまたはディレクトリが選択されていません"
    return 1
  fi

  save_history git show "${hash}":"$target"
}

# GitHubのPRのようなブランチ間差分表示（共通祖先からの差分）
function fgd2(){
  local base
  base=$(FZF_DEFAULT_OPTS="--prompt='base: ' --header='比較元ブランチを選択'" br_org)
  local ret=$?
  if [[ $ret -ne 0 || -z $base ]]; then
    return 1
  fi
  local compare
  compare=$(FZF_DEFAULT_OPTS="--prompt='compare: ' --header='比較先ブランチを選択'" br_org)
  ret=$?
  if [[ $ret -ne 0 || -z $compare ]]; then
    return 1
  fi
  save_history git diff "$@" $base...$compare
}

# GitHubのPRのようなブランチ間ログ表示（共通祖先からの差分）
function fgl2(){
  local base
  base=$(FZF_DEFAULT_OPTS="--prompt='base: ' --header='比較元ブランチを選択'" br_org)
  local ret=$?
  if [[ $ret -ne 0 || -z $base ]]; then
    return 1
  fi
  local compare
  compare=$(FZF_DEFAULT_OPTS="--prompt='compare: ' --header='比較先ブランチを選択'" br_org)
  ret=$?
  if [[ $ret -ne 0 || -z $compare ]]; then
    return 1
  fi
  save_history git log "$@" $base..$compare
}

# 差分のあるファイルを選択してdiffを表示
function fgds() {
  # 変更のあるファイルとディレクトリのリストを生成
selection=$(
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
)

# 選択されたものがあれば処理を続行
if [ -n "$selection" ]; then
    git diff --color=always -- "$selection" | less -R
fi
}