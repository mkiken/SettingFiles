#!/bin/zsh

source "$(dirname "$0")/../common.sh"

echo "Setting up other AI assistants..."

# for Cursor/Roo
mkdir -p ~/.roo/rules
make_symlink "${Repo}ai/common/prompt.md" ~/.roo/rules/.roorules

echo 'Other AI assistants setup completed.'