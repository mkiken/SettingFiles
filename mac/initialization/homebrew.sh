#!/bin/zsh

source "$(dirname "${(%):-%x}")/../scripts/common.sh"

if ! command -v brew > /dev/null 2>&1; then
  if [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [[ -x /usr/local/bin/brew ]]; then
    eval "$(/usr/local/bin/brew shellenv)"
  else
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  fi
fi

if ! command -v brew > /dev/null 2>&1; then
  if [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [[ -x /usr/local/bin/brew ]]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
fi

if ! command -v brew > /dev/null 2>&1; then
  echo "Error: Homebrew installation failed or brew is not on PATH." >&2
  return 1 2>/dev/null || exit 1
fi

brew_prefix="$(brew --prefix)"
profile_line="[[ -f ${brew_prefix}/bin/brew ]] && eval \"\$(${brew_prefix}/bin/brew shellenv)\""

if ! /usr/bin/grep -Fqx "$profile_line" "$HOME/.zprofile" 2>/dev/null; then
  echo >> "$HOME/.zprofile"
  print -r -- "$profile_line" >> "$HOME/.zprofile"
fi

untap_stale_homebrew_taps
brew bundle --file="${Repo}mac/Brewfile" -v
