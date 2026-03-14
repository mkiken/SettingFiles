#!/bin/zsh

# 関数定義を読み込み
source "$(dirname "$(dirname "$(dirname "$(realpath "$0")")")")/shell/zsh/alias/utils.zsh"

# set Repo "$HOME/Desktop/repository/SettingFiles/"
Repo="$(dirname "$(dirname "$(dirname "$(realpath "$0")")")")/"
Repo_shell="${Repo}shell/"
