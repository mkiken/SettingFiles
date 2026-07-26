#!/bin/zsh

function setup_mdts_config() {
  local repo_root="${1:-$Repo}"
  local target_home="${2:-$HOME}"
  local source_config="${repo_root%/}/terminal/mdts/config.json"
  local live_config="$target_home/.config/mdts/config.json"
  local existing_target=""

  if [[ ! -f "$source_config" ]]; then
    echo "Error: managed mdts config is unavailable: $source_config" >&2
    return 1
  fi

  if [[ -L "$live_config" ]]; then
    existing_target="$(readlink "$live_config")"
    if [[ "$existing_target" == "$source_config" ]]; then
      echo "✓ Already linked: $live_config -> $source_config"
      return 0
    fi
    echo "Error: mdts config uses an unexpected symlink target: $existing_target" >&2
    return 1
  elif [[ -e "$live_config" ]]; then
    echo "Error: refusing to replace existing mdts config: $live_config" >&2
    return 1
  fi

  mkdir -p "$(dirname "$live_config")" || return 1
  make_symlink "$source_config" "$live_config"
}

function setup_mdts() {
  local repo_root="${1:-$Repo}"
  local target_home="${2:-$HOME}"

  setup_mdts_config "$repo_root" "$target_home" || return 1
  return 0
}
