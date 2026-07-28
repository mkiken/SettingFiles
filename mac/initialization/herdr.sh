#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"
source "${Repo}mac/scripts/herdr.sh"

echo "Setting up Herdr..."
setup_herdr "" "" install || exit 1
echo "Herdr setup completed."
