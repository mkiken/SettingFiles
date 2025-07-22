#!/bin/zsh

source "$(dirname "$0")/common.sh"

# Shell
make_symlink "${Repo_shell}bash/.bash_profile" ~/
make_symlink "${Repo_shell}zsh/.zshrc" ~/

# Ghostty
mkdir -p ~/.config/ghostty
make_symlink "${Repo}terminal/ghostty/config" ~/.config/ghostty

# Vim/Neovim
make_symlink "${Repo}vimfiles/nvim" ~/.config

# IDEAVim
make_symlink "${Repo}.ideavimrc" ~/.ideavimrc

# Tmux
make_symlink "${Repo}.tmux.conf" ~/.tmux.conf

# Tmux Plugin Manager
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm

# Ranger
mkdir -p ~/.config
make_symlink "${Repo}ranger" ~/.config

# Karabiner
mkdir -p ~/.config/karabiner
make_symlink "${Repo}mac/karabiner.json" ~/.config/karabiner

# History file
touch ~/.cd_history_file

echo 'Development tools configured.'