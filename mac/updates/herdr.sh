#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"
source "${Repo}mac/scripts/herdr.sh"

echo "Refreshing Herdr configuration and integrations..."
# mac/update から source される前提。exit すると呼び出し元(mac/update)ごと
# 終了してしまうため、return で自分自身の残り処理だけを打ち切る。
setup_herdr "" "" update || return 1
echo "Herdr update completed."
