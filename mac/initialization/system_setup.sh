#!/bin/zsh

source "$(dirname "$0")/common.sh"

# El Capitanにアップデートした後、gitコマンドが以下のエラーを吐いて動かなくなる問題
# http://qiita.com/Ys_Jn/items/f7ff03f7a890329c3e2a
xcode-select --install

# Shell setting
sudo chsh -s /usr/local/bin/zsh

echo "please install Sauce Code Pro Nerd Font Complete.ttf at https://www.nerdfonts.com/font-downloads."
echo "please press ^T-I in tmux to install tmux plugins."

echo 'System setup completed.'