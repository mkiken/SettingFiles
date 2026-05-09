#!/bin/zsh

source "$(dirname "$0")/../../scripts/common.sh"

echo "Setting up Codex..."

npm install -g @openai/codex

# 共通設定テンプレートを ~/.codex/config.toml にマージ
smart_merge_toml "${Repo}ai/codex/config.toml" ~/.codex/config.toml

# 共通プロンプトを連結して _AGENTS.md を生成し、~/.codex/AGENTS.md にシンボリックリンク
{ /bin/cat "${Repo}ai/common/prompt_base.md"; echo; /bin/cat "${Repo}ai/common/characters/mizuki_himeji.md"; echo; /bin/cat "${Repo}ai/codex/codex_base.md"; } > "${Repo}ai/codex/_AGENTS.md"
make_symlink "${Repo}ai/codex/_AGENTS.md" ~/.codex/AGENTS.md

# hooks はファイル単位でシンボリックリンク
mkdir -p ~/.codex/hooks
for file in "${Repo}ai/codex/hooks"/*; do
  if [[ -f "$file" ]]; then
    make_symlink "$file" ~/.codex/hooks/$(basename "$file")
  fi
done

# hooks.json をシンボリックリンク
make_symlink "${Repo}ai/codex/hooks.json" ~/.codex/hooks.json

chmod +x ~/.codex/hooks/codex-stop-notification.sh

# rules はファイル単位でシンボリックリンク
rules_dest=~/.codex/rules
mkdir -p "$rules_dest"
for file in "${Repo}ai/codex/rules"/*; do
  if [[ -f "$file" ]]; then
    make_symlink "$file" "${rules_dest}/$(basename "$file")"
  fi
done

# agents はファイル単位でシンボリックリンク
agents_dest=~/.codex/agents
mkdir -p "$agents_dest"
for file in "${Repo}ai/codex/agents"/*; do
  if [[ -f "$file" ]]; then
    make_symlink "$file" "${agents_dest}/$(basename "$file")"
  fi
done

# skills はディレクトリ単位でシンボリックリンク（skills/<name>/SKILL.md 構造のため）
skills_dest=~/.codex/skills
mkdir -p "$skills_dest"
for skill_dir in "${Repo}ai/codex/skills"/*/; do
  if [[ -d "$skill_dir" ]]; then
    skill_name=$(basename "$skill_dir")
    make_symlink "$skill_dir" "${skills_dest}/${skill_name}"
  fi
done

npm install -g @nogataka/ccresume-codex

echo "Codex setup completed."
