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

# Copy file only if destination does not exist (with warning if it exists)
function copy_if_not_exists() {
    local src="$1"
    local dst="$2"

    if [[ -z "$src" || -z "$dst" ]]; then
        echo "Usage: copy_if_not_exists <source> <destination>"
        return 1
    fi

    local cmd="cp -n \"$src\" \"$dst\""
    echo "$cmd"
    if eval "$cmd"; then
        return 0
    else
        echo "\n⚠️  Warning: $dst already exists. Please remove it first.\n"
        return 1
    fi
}

# set Repo "$HOME/Desktop/repository/SettingFiles/"
Repo="$(dirname "$(dirname "$(dirname "$(realpath "$0")")")")/"
Repo_shell="${Repo}shell/"