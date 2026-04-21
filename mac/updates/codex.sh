#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"

echo "Updating Codex tools..."

npm i -g @openai/codex@latest

echo "Codex tools update completed."
