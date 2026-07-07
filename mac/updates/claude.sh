#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"
source "${Repo}mac/scripts/ai/claude.sh"

echo "Updating Claude tools..."

setup_ai_mcp update
setup_ai_pr_tools

smart_merge_json ~/.claude/settings.json "${Repo}ai/claude/settings.json"

# コマンド内の実行時 cat が依存する共通ディレクトリリンクを再作成（消失時の自己修復）
make_symlink "${Repo}ai/common" ~/.claude/common

# pr-review-subagents のレビュアー定義を共有フラグメントから生成（編集は ai/common/pr_review_subagents/ と ai/claude/agents_src/ へ）
generate_pr_reviewer_agents claude

setup_ai_skills ~/.claude/skills "${Repo}ai/common/skills" "${Repo}ai/claude/skills"

claude update
setup_claude_superpowers
setup_claude_context_mode
setup_claude_mem

echo "Claude tools update completed."
