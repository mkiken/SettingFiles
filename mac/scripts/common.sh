#!/bin/zsh

# 関数定義を読み込み
source "$(dirname "$(dirname "$(dirname "$(realpath "${(%):-%x}")")")")/shell/zsh/alias/utils.zsh"

# set Repo "$HOME/Desktop/repository/SettingFiles/"
Repo="$(dirname "$(dirname "$(dirname "$(realpath "${(%):-%x}")")")")/"
Repo_shell="${Repo}shell/"

function untap_stale_homebrew_taps() {
  local stale_taps=(
    "aku11i/tap"
    "dwarvesf/tap"
    "dwarvesf/homebrew-tap"
  )

  local stale_tap
  for stale_tap in "${stale_taps[@]}"; do
    if HOMEBREW_NO_AUTO_UPDATE=1 brew tap | /usr/bin/grep -Fxq "$stale_tap"; then
      HOMEBREW_NO_AUTO_UPDATE=1 brew untap "$stale_tap"
    fi
  done
}

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

function setup_ai_pr_tools() {
  local source_dir="${Repo}shell/common/pr"
  local dest_bin="$HOME/.config/ai-pr/bin"
  local file

  if [[ -d "$dest_bin" && ! -L "$dest_bin" ]]; then
    for file in "${source_dir}"/*.sh; do
      if [[ -f "$file" ]]; then
        make_symlink "$file" "${dest_bin}/$(basename "$file")"
      fi
    done
    return
  fi

  make_symlink "$source_dir" "$dest_bin"
}
