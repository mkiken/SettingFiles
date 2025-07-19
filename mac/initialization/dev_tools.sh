#!/usr/local/bin/zsh

source "$(dirname "$0")/common.sh"

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

# Shell
make_symlink "${Repo_shell}bash/.bashrc" ~/
make_symlink "${Repo_shell}zsh/.zshrc" ~/

# History file
touch ~/.cd_history_file

echo 'Development tools configured.'