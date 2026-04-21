#!/bin/zsh

source "$(dirname "$0")/../../scripts/common.sh"

echo "Setting up Codex..."

npm install -g @openai/codex

echo "Codex setup completed."
