#!/bin/zsh

function make_symlink () {
  # リンク先のディレクトリを取得
  local target_dir="$(dirname "$2")"
  
  # ディレクトリが存在しない場合は作成
  if [[ ! -d "$target_dir" ]]; then
    echo "mkdir -p $target_dir"
    mkdir -p "$target_dir"
  fi
  
  echo "ln -si $1 $2"
  ln -si "$1" "$2"
}

# set Repo "$HOME/Desktop/repository/SettingFiles/"
Repo="$(dirname "$(dirname "$(dirname "$(realpath "$0")")")")/"
Repo_shell="${Repo}shell/"