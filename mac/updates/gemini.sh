#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"

echo "Updating Gemini tools..."

smart_merge_json ~/.gemini/settings.json "${Repo}ai/gemini/settings.json"

pipx upgrade SuperGemini
SuperGemini update

echo "Gemini tools update completed."
