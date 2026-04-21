#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"

echo "Updating Codex tools..."

npm i -g @openai/codex@latest

# 共通設定テンプレートを ~/.codex/config.toml にマージ
smart_merge_toml "${Repo}ai/codex/config.toml" ~/.codex/config.toml

echo "Codex tools update completed."
