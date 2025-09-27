#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"

# touch ~/.gitconfig.local
cp -i "${Repo}gitfiles/.gitconfig.local_mac" ~/.os.gitconfig

cp -i "${Repo}gitfiles/hooks/commit-msg" ${Repo}.git/hooks

echo 'files copied.'