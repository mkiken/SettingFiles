#!/usr/local/bin/zsh

source "$(dirname "$0")/common.sh"

# touch ~/.gitconfig.local
cp -i "${Repo}gitfiles/.gitconfig.local_mac" ~/.os.gitconfig
echo "You can write LOCAL settings for git to '~/.gitconfig.local'."

cp -i "${Repo}gitfiles/hooks/commit-msg" ${Repo}.git/hooks

echo 'files copied.'