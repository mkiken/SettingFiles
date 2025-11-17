#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"

# touch ~/.gitconfig.local
smart_copy "${Repo}gitfiles/.gitconfig.local_mac" ~/.os.gitconfig

smart_copy "${Repo}gitfiles/hooks/commit-msg" ${Repo}.git/hooks/commit-msg

echo 'files copied.'