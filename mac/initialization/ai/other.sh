#!/bin/zsh

source "$(dirname "$0")/../common.sh"

echo "Setting up other AI assistants..."

# for serena
mkdir -p ~/.serena
cmd="cp -n \"${Repo}ai/serena/serena_config.yml\" ~/.serena/"
echo "$cmd"
if ! eval "$cmd"; then
    echo "\nWarning: ~/.serena/serena_config.yml already exists. Please remove it first.\n"
fi

# for Cursor/Roo
mkdir -p ~/.roo/rules
make_symlink "${Repo}ai/common/prompt.md" ~/.roo/rules/.roorules

echo 'Other AI assistants setup completed.'