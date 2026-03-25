#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"

# Shell
make_symlink "${Repo_shell}bash/.bash_profile" ~/
make_symlink "${Repo_shell}zsh/.zshrc" ~/

# Ghostty
make_symlink "${Repo}terminal/ghostty/config" ~/.config/ghostty/config

# Atuin
make_symlink "${Repo}terminal/atuin/config.toml" ~/.config/atuin/config.toml

# Vim/Neovim
make_symlink "${Repo}vimfiles/nvim" ~/.config

# IDEAVim
make_symlink "${Repo}.ideavimrc" ~/.ideavimrc

# Tmux
make_symlink "${Repo}.tmux.conf" ~/.tmux.conf
make_symlink "${Repo}shell/tmux/new-window.py" ~/.tmux/scripts/new-window.py
make_symlink "${Repo}shell/tmux/sort-windows.py" ~/.tmux/scripts/sort-windows.py

# Tmux Plugin Manager
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm

# Karabiner
smart_merge_json "${Repo}mac/karabiner.json" ~/.config/karabiner/karabiner.json

# VSCode
smart_merge_json "${Repo}vscode/base_setting.json" ~/Library/Application\ Support/Code/User/settings.json
smart_copy "${Repo}vscode/base_keybindings.json" ~/Library/Application\ Support/Code/User/keybindings.json

# commitlint
npm install -g @commitlint/config-conventional

echo 'Development tools configured.'