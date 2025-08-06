#!/bin/zsh

source "$(dirname "$0")/common.sh"

# Shell setting
sudo chsh -s /bin/zsh

echo "please install Sauce Code Pro Nerd Font Complete.ttf at https://www.nerdfonts.com/font-downloads."
echo "please press ^T-I in tmux to install tmux plugins."

echo 'System setup completed.'