#!/bin/zsh

source "$(dirname "$0")/../../scripts/common.sh"

echo "Setting up other AI assistants..."

# for serena
copy_if_not_exists "${Repo}ai/serena/serena_config.yml" ~/.serena/serena_config.yml

# for Roo Code
make_symlink "${Repo}ai/common/prompt.md" ~/.roo/rules/.roorules

# for Cursor
make_symlink "${Repo}ai/common/mcp.json" ~/.cursor/mcp.json

# for Spec Kit
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git

echo 'Other AI assistants setup completed.'
