#!/bin/zsh

source "$(dirname "$0")/../../scripts/common.sh"

echo "Setting up Gemini..."

# jqコマンドの確認
if ! command -v jq &> /dev/null; then
    echo "Error: jq is not installed. Please install it with 'brew install jq'"
    exit 1
fi

# Gemini setup
cat "${Repo}ai/common/prompt_base.md" > "${Repo}ai/gemini/_GEMINI.md"
echo "UPDATE ${Repo}ai/gemini/_GEMINI.md!"

# JSONマージ処理
echo "Merging MCP configuration into settings.json..."
jq -s '.[0] * .[1]' "${Repo}ai/gemini/settings.json" "${Repo}ai/common/mcp.json" > "${Repo}ai/gemini/settings.json.tmp"
mv "${Repo}ai/gemini/settings.json.tmp" "${Repo}ai/gemini/settings.json"
echo "MCP configuration merged successfully!"

make_symlink "${Repo}ai/gemini/_GEMINI.md" ~/.gemini/GEMINI.md
make_symlink "${Repo}ai/gemini/settings.json" ~/.gemini/settings.json

echo "Installing Gemini tools..."

# Gemini tools
npm install -g @google/gemini-cli

echo 'Gemini setup and tools installation completed.'