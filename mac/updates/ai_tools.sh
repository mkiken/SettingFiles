#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"

echo "Updating AI tools..."

smart_copy ~/.gemini/settings.json "${SET}ai/gemini/settings.json"

# Claude更新
echo "Updating Claude tools..."
SuperClaude update

echo "AI tools update completed."
