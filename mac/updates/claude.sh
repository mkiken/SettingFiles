#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"

echo "Updating Claude tools..."

smart_merge_json ~/.claude/settings.json "${Repo}ai/claude/settings.json"

claude update

pipx upgrade SuperClaude
SuperClaude update

echo "Claude tools update completed."
