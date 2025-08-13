#!/bin/zsh

source "$(dirname "$0")/../common.sh"

echo "Setting up other AI assistants..."

# for serena
cmd="cp -n \"${Repo}ai/serena/serena_config.yml\" ~/.serena/serena_config.yml"
echo "$cmd"
if ! eval "$cmd"; then
    echo "\nWarning: ~/.serena/serena_config.yml already exists. Please remove it first.\n"
fi

# for Roo Code
make_symlink "${Repo}ai/common/prompt.md" ~/.roo/rules/.roorules

# for Cursor
make_symlink "${Repo}ai/common/mcp.json" ~/.cursor/mcp.json

echo 'Other AI assistants setup completed.'
