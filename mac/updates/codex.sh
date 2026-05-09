#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"

echo "Updating Codex tools..."

npm i -g @openai/codex@latest

# 共通設定テンプレートを ~/.codex/config.toml にマージ
smart_merge_toml "${Repo}ai/codex/config.toml" ~/.codex/config.toml

# 共通プロンプトの更新を _AGENTS.md に反映
{ /bin/cat "${Repo}ai/common/prompt_base.md"; echo; /bin/cat "${Repo}ai/common/characters/mizuki_himeji.md"; echo; /bin/cat "${Repo}ai/codex/codex_base.md"; } > "${Repo}ai/codex/_AGENTS.md"

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

echo "Codex tools update completed."
