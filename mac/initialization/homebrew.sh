#!/bin/zsh

source "$(dirname "$0")/common.sh"

# install commands

/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"


if ! command -v brew > /dev/null 2>&1; then
  if [ -f /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
    echo >> "$HOME/.zprofile"
    echo '[[ -f /opt/homebrew/bin/brew ]] && eval "$(/opt/homebrew/bin/brew shellenv)"' >> "$HOME/.zprofile"
  fi
fi

brew bundle -v

make_symlink "${BREW_PREFIX}/share/git-core/contrib/diff-highlight/diff-highlight" /usr/local/bin