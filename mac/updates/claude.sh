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
generate_pr_review_verifier_agents claude

# config-audit の監査エージェント定義を共有フラグメントから生成（編集は ai/common/config_audit_subagents/ と ai/claude/agents_src/config_audit/ へ）
generate_config_auditor_agents claude

# audit-fix の設計/実装サブエージェント定義を共有フラグメントから生成（編集は ai/common/audit_fix_subagents/ と ai/claude/agents_src/audit_fix/ へ）
generate_audit_fix_agents claude

# agents はファイル単位でシンボリックリンク（生成分の反映）
mkdir -p ~/.claude/agents
for file in "${Repo}ai/claude/agents"/*; do
  if [[ -f "$file" ]]; then
    make_symlink "$file" ~/.claude/agents/$(basename "$file")
  fi
done

# herdr 公式スキルの upstream 更新を取り込む（差分があれば repo 内ファイルを上書きするが
# git add はしない — コミット判断は `git diff` で人間がレビューしてから行う）
sync_herdr_skill

setup_ai_skills ~/.claude/skills "${Repo}ai/common/skills" "${Repo}ai/claude/skills"

claude update
setup_claude_superpowers
setup_claude_context_mode
setup_claude_rtk
setup_claude_genshijin
setup_claude_dig
setup_claude_example_skills
setup_claude_mem

echo "Claude tools update completed."
