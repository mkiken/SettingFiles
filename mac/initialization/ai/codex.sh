#!/bin/zsh

source "$(dirname "$0")/../../scripts/common.sh"

echo "Setting up Codex..."

npm install -g @openai/codex

# skills はディレクトリ単位でシンボリックリンク（skills/<name>/SKILL.md 構造のため）
skills_dest=~/.codex/skills
mkdir -p "$skills_dest"
for skill_dir in "${Repo}ai/codex/skills"/*/; do
  if [[ -d "$skill_dir" ]]; then
    skill_name=$(basename "$skill_dir")
    make_symlink "$skill_dir" "${skills_dest}/${skill_name}"
  fi
done

echo "Codex setup completed."
