#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"
source "${Repo}mac/scripts/herdr.sh"

echo "Refreshing Herdr configuration and integrations..."
setup_herdr "" "" update || exit 1
echo "Herdr update completed."
