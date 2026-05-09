#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"

echo "Updating Gemini settings..."

setup_ai_mcp update

smart_merge_json ~/.gemini/settings.json "${Repo}ai/gemini/settings.json"

echo "Gemini settings update completed."
