#!/bin/zsh

# 関数定義を読み込み
source "$(dirname "$(dirname "$(dirname "$(realpath "$0")")")")/shell/zsh/alias/utils.zsh"

# set Repo "$HOME/Desktop/repository/SettingFiles/"
Repo="$(dirname "$(dirname "$(dirname "$(realpath "$0")")")")/"
Repo_shell="${Repo}shell/"

function setup_ai_skills() {
  local dest_dir="$1"
  shift

  mkdir -p "$dest_dir"

  local skills_root skill_dir skill_name
  for skills_root in "$@"; do
    if [[ ! -d "$skills_root" ]]; then
      continue
    fi

    for skill_dir in "${skills_root}"/*(/N); do
      skill_name=$(basename "$skill_dir")
      make_symlink "$skill_dir" "${dest_dir}/${skill_name}"
    done
  done
}
