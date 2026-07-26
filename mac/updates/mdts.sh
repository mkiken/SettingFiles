#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"
source "${Repo}mac/scripts/mdts.sh"

echo "Refreshing mdts configuration..."
setup_mdts || exit 1
echo "mdts update completed."
