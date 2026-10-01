#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"
source "${Repo}mac/scripts/ai/codex.sh"

echo "Updating Codex tools..."

npm i -g @openai/codex@latest

# cc-sdd Codex Skills はホームディレクトリで更新する
(cd "$HOME" && npx --yes cc-sdd@latest --codex-skills --lang ja --manifest "${Repo}ai/codex/cc-sdd-codex-skills-no-agents.json" --overwrite force)

setup_ai_mcp update
setup_ai_pr_tools
# mac/update から source される前提。exit すると呼び出し元(mac/update)ごと
# 終了してしまうため、return で自分自身の残り処理だけを打ち切る。
update_codex_caveman || return 1

generate_codex_agents

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
generate_pr_review_verifier_agents codex

# config-audit の監査エージェント定義を共有フラグメントから生成（編集は ai/common/config_audit_subagents/ と ai/codex/agents_src/config_audit/ へ）
generate_config_auditor_agents codex || return 1

# review-fix の設計/実装サブエージェント定義を共有フラグメントから生成（編集は ai/common/review_fix_subagents/ と ai/codex/agents_src/review_fix/ へ）
generate_review_fix_agents

# audit-fix の設計/実装サブエージェント定義を共有フラグメントから生成（編集は ai/common/audit_fix_subagents/ と ai/codex/agents_src/audit_fix/ へ）
generate_audit_fix_agents codex

# config-audit の6ロールと audit-fix の2ロールは実ファイル、ほかの agents はシンボリックリンク
agents_dest=~/.codex/agents
mkdir -p "$agents_dest"
setup_codex_regular_file_agents || return 1
for file in "${Repo}ai/codex/agents"/*; do
  case "${file:t}" in
    config_auditor_(default|conflict|overlap|patch|ambiguity|concise).toml|audit_fix_(designer|implementer).toml) continue ;;
  esac
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
setup_codex_rtk
setup_codex_claude_mem
setup_codex_ponytail

# 共通設定テンプレートを ~/.codex/config.toml にマージ
smart_merge_toml "${Repo}ai/codex/config.toml" ~/.codex/config.toml

echo "Codex tools update completed."
