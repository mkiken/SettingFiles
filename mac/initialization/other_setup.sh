#!/bin/zsh

source "$(dirname "$0")/common.sh"

make_symlink "${Repo}vimfiles/nvim" ~/.config

# touch ~/.z
touch ~/.cd_history_file

# El Capitanにアップデートした後、gitコマンドが以下のエラーを吐いて動かなくなる問題
# http://qiita.com/Ys_Jn/items/f7ff03f7a890329c3e2a
xcode-select --install

# for Tmux Plugin Manager
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm

# shell setting
sudo chsh -s /usr/local/bin/zsh

# for gh
gh extension install dlvhdr/gh-dash
gh extension install gennaro-tedesco/gh-f

git submodule update --init

# for Claude
npm install -g @anthropic-ai/claude-code
npm install -g ccusage
npm install -g @sasazame/ccresume

claude mcp add sequential-thinking -s user -- npx -y @modelcontextprotocol/server-sequential-thinking

#for Gemini
npm install -g @google/gemini-cli

echo "please install Sauce Code Pro Nerd Font Complete.ttf at https://www.nerdfonts.com/font-downloads."
echo "please press ^T-I in tmux to install tmux plugins."