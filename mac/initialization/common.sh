#!/usr/local/bin/zsh

function make_symlink () {
  echo "ln -si $1 $2"
  ln -si "$1" "$2"
}

# set Repo "$HOME/Desktop/repository/SettingFiles/"
Repo="$(dirname "$(dirname "$(dirname "$(realpath "$0")")")")/"
Repo_shell="${Repo}shell/"