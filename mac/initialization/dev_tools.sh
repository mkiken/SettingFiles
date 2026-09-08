#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"

# Shell
ensure_settingfiles_shell_loader ~/.zshrc        "${Repo_shell}zsh/managed.zsh"   zsh
ensure_settingfiles_shell_loader ~/.bash_profile "${Repo_shell}bash/managed.bash" bash

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

# mdv: ローカルMarkdownビューア（SDDのspec/planをブラウザでツリー表示する）
go install github.com/gr1m0h/mdv@latest

echo 'Development tools configured.'
