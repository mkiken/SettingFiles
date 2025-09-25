#!/bin/zsh

source "$(dirname "$0")/common.sh"

# Git symlinks
make_symlink "${Repo}gitfiles/.gitconfig" ~/.gitconfig
make_symlink "${Repo}gitfiles/.gitignore_global" ~/.gitignore
make_symlink "${Repo}gitfiles/.git_template" ~
make_symlink "${Repo}gitfiles/gitui" "$HOME/.config"
make_symlink "${Repo}gitfiles/gh/dash/config.yml" "$HOME/.config/gh-dash/config.yml"

# Git extensions
gh extension install dlvhdr/gh-dash
gh extension install gennaro-tedesco/gh-f

# Git submodules
git submodule update --init

echo 'Git configuration completed.'