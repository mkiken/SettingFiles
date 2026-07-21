#!/bin/zsh

source "$(dirname "$0")/../../scripts/common.sh"
source "${Repo}mac/scripts/ai/codex.sh"

echo "Setting up Codex..."

npm install -g @openai/codex

# cc-sdd Codex Skills はホームディレクトリにインストールする
(cd "$HOME" && npx --yes cc-sdd@latest --codex-skills --lang ja --manifest "${Repo}ai/codex/cc-sdd-codex-skills-no-agents.json" --overwrite force)

setup_ai_mcp install
setup_ai_pr_tools

# 共通プロンプトを連結して _AGENTS.md を生成し、~/.codex/AGENTS.md にシンボリックリンク
generate_codex_agents
make_symlink "${Repo}ai/codex/_AGENTS.md" ~/.codex/AGENTS.md

# hooks はファイル単位でシンボリックリンク
mkdir -p ~/.codex/hooks
for file in "${Repo}ai/codex/hooks"/*; do
  if [[ "$(basename "$file")" == test_*.py ]]; then
    continue
  elif [[ -f "$file" ]]; then
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

# pr-review-subagents のレビュアー定義を共有フラグメントから生成（編集は ai/common/pr_review_subagents/ と ai/codex/agents_src/ へ）
generate_pr_reviewer_agents codex

# config-audit の監査エージェント定義を共有フラグメントから生成（編集は ai/common/config_audit_subagents/ と ai/codex/agents_src/config_audit/ へ）
generate_config_auditor_agents codex

# agents はファイル単位でシンボリックリンク
agents_dest=~/.codex/agents
mkdir -p "$agents_dest"
for file in "${Repo}ai/codex/agents"/*; do
  if [[ -f "$file" ]]; then
    make_symlink "$file" "${agents_dest}/$(basename "$file")"
  fi
done

# 共有コアスキルの SKILL.md をソース連結で生成（編集は各 skill_head.md / skill_tail.md / ai/common のコアへ）
generate_codex_skills

# skills はディレクトリ単位でシンボリックリンク（skills/<name>/SKILL.md 構造のため）
setup_ai_skills ~/.codex/skills "${Repo}ai/common/skills" "${Repo}ai/codex/skills"

setup_codex_superpowers
setup_codex_context_mode
setup_codex_claude_mem

npm install -g @nogataka/ccresume-codex

# 共通設定テンプレートを ~/.codex/config.toml にマージ
smart_merge_toml "${Repo}ai/codex/config.toml" ~/.codex/config.toml
setup_gsd_core_for_runtime codex install || exit 1

echo "Codex setup completed."
