#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"

# Shell
make_symlink "${Repo_shell}bash/.bash_profile" ~/
make_symlink "${Repo_shell}zsh/.zshrc" ~/

# Ghostty
make_symlink "${Repo}terminal/ghostty/config" ~/.config/ghostty/config

# Vim/Neovim
make_symlink "${Repo}vimfiles/nvim" ~/.config

# IDEAVim
make_symlink "${Repo}.ideavimrc" ~/.ideavimrc

# Tmux
make_symlink "${Repo}.tmux.conf" ~/.tmux.conf

# Tmux Plugin Manager
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm

# Ranger
make_symlink "${Repo}ranger" ~/.config/ranger

# Karabiner
make_symlink "${Repo}mac/karabiner.json" ~/.config/karabiner/karabiner.json

# VSCode
copy_if_not_exists "${Repo}vscode/base_setting.json" ~/Library/Application\ Support/Code/User/settings.json

# History file
touch ~/.cd_history_file

# commitlint
npm install -g @commitlint/config-conventional

echo 'Development tools configured.'