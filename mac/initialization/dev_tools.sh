#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"

# Shell
make_symlink "${Repo_shell}bash/.bash_profile" ~/
ensure_settingfiles_zsh_loader ~/.zshrc "${Repo_shell}zsh/managed.zsh"

# Ghostty
make_symlink "${Repo}terminal/ghostty/config" ~/.config/ghostty/config

# Atuin
make_symlink "${Repo}terminal/atuin/config.toml" ~/.config/atuin/config.toml

# Vim/Neovim
make_symlink "${Repo}vimfiles/nvim" ~/.config

# IDEAVim
make_symlink "${Repo}.ideavimrc" ~/.ideavimrc

# Karabiner
smart_merge_json "${Repo}mac/karabiner.json" ~/.config/karabiner/karabiner.json

# VSCode
smart_copy "${Repo}vscode/base_setting.jsonc" ~/Library/Application\ Support/Code/User/settings.json
smart_copy "${Repo}vscode/base_keybindings.json" ~/Library/Application\ Support/Code/User/keybindings.json

# commitlint
npm install -g @commitlint/config-conventional

echo 'Development tools configured.'
