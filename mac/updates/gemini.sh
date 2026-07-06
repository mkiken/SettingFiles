#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"
source "${Repo}mac/scripts/ai/gemini.sh"

echo "Updating Gemini settings..."

homebrew_npm install -g @google/gemini-cli@latest

setup_ai_mcp update
setup_ai_pr_tools

smart_merge_json ~/.gemini/settings.json "${Repo}ai/gemini/settings.json"

# pr-review-subagents のレビュアー定義を共有フラグメントから生成（編集は ai/common/pr_review_subagents/ と ai/gemini/agents_src/ へ）
generate_pr_reviewer_agents gemini

setup_ai_skills ~/.gemini/skills "${Repo}ai/common/skills" "${Repo}ai/gemini/skills"

setup_gemini_superpowers
setup_gemini_context_mode
setup_gemini_claude_mem

echo "Gemini settings update completed."
