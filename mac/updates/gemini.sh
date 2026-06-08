#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"

echo "Updating Gemini settings..."

setup_ai_mcp update
setup_ai_pr_tools

smart_merge_json ~/.gemini/settings.json "${Repo}ai/gemini/settings.json"

setup_ai_skills ~/.gemini/skills "${Repo}ai/common/skills" "${Repo}ai/gemini/skills"

echo "Gemini settings update completed."
