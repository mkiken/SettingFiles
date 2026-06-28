#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"

echo "Updating Claude tools..."

setup_ai_mcp update
setup_ai_pr_tools

smart_merge_json ~/.claude/settings.json "${Repo}ai/claude/settings.json"

setup_ai_skills ~/.claude/skills "${Repo}ai/common/skills" "${Repo}ai/claude/skills"

claude update
setup_claude_superpowers

echo "Claude tools update completed."
