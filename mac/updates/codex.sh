#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"

echo "Updating Codex tools..."

npm i -g @openai/codex@latest

# 共通設定テンプレートを ~/.codex/config.toml にマージ
smart_merge_toml ~/.codex/config.toml "${Repo}ai/codex/config.toml"

# 共通プロンプトの更新を _AGENTS.md に反映
{ /bin/cat "${Repo}ai/common/prompt_base.md"; echo; /bin/cat "${Repo}ai/common/characters/mizuki_himeji.md"; } > "${Repo}ai/codex/_AGENTS.md"

echo "Codex tools update completed."
