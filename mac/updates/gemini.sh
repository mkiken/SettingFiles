#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"
source "${Repo}mac/scripts/ai/gemini.sh"

echo "Updating Gemini settings..."

homebrew_npm install -g @google/gemini-cli@latest

setup_ai_mcp update
setup_ai_pr_tools

# Gemini の常時読み込みルールを upstream と同期する。
sync_genshijin_rule

smart_merge_json ~/.gemini/settings.json "${Repo}ai/gemini/settings.json"

# コマンド内の実行時 cat が依存する共通ディレクトリリンクを再作成（消失時の自己修復）
make_symlink "${Repo}ai/common" ~/.gemini/common
# Gemini CLI loads ~/.gemini/.env; keep AI-launched notifications suppressed.
sync_gemini_env_home_to_repo
sync_gemini_env_repo_to_home

# pr-review-subagents のレビュアー定義を共有フラグメントから生成（編集は ai/common/pr_review_subagents/ と ai/gemini/agents_src/ へ）
generate_pr_reviewer_agents gemini

# config-audit の監査エージェント定義を共有フラグメントから生成（編集は ai/common/config_audit_subagents/ と ai/gemini/agents_src/config_audit/ へ）
generate_config_auditor_agents gemini

# agents はファイル単位でシンボリックリンク（生成分の反映）
mkdir -p ~/.gemini/agents
for file in "${Repo}ai/gemini/agents"/*; do
  if [[ "$(basename "$file")" == test_*.py ]]; then
    continue
  elif [[ -f "$file" ]]; then
    make_symlink "$file" ~/.gemini/agents/$(basename "$file")
  fi
done

# 共有コアスキルの SKILL.md を生成（編集はソースの skill_head.md / skill_tail.md / ai/common のコアへ）
generate_gemini_skills

setup_ai_skills ~/.gemini/skills "${Repo}ai/common/skills" "${Repo}ai/gemini/skills"

setup_gemini_superpowers
setup_gemini_context_mode
setup_gemini_rtk
setup_gemini_claude_mem

echo "Gemini settings update completed."
