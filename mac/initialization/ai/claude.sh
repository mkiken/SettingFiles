#!/bin/zsh

source "$(dirname "$0")/../../scripts/common.sh"
source "${Repo}mac/scripts/ai/claude.sh"

echo "Setting up Claude..."

setup_ai_mcp install
setup_ai_pr_tools

# Claude setup
echo "UPDATE ${Repo}ai/claude/_CLAUDE.md!"

make_symlink "${Repo}ai/claude/_CLAUDE.md" ~/.claude/CLAUDE.md
make_symlink "${Repo}ai/common" ~/.claude/common

make_symlink "${Repo}ai/claude/statusline-command.sh" ~/.claude/statusline-command.sh

for item in settings.json; do
  smart_merge_json "${Repo}ai/claude/${item}" ~/.claude/${item}
done

# pr-review-subagents のレビュアー定義を共有フラグメントから生成（編集は ai/common/pr_review_subagents/ と ai/claude/agents_src/ へ）
generate_pr_reviewer_agents claude

# config-audit の監査エージェント定義を共有フラグメントから生成（編集は ai/common/config_audit_subagents/ と ai/claude/agents_src/config_audit/ へ）
generate_config_auditor_agents claude

# agents,hooks,scripts はディレクトリ内のファイルをシンボリックリンク
for item in agents hooks scripts; do
  dest_dir=~/.claude/${item}

  mkdir -p "$dest_dir"

  for file in "${Repo}ai/claude/${item}"/*; do
    if [[ -f "$file" ]]; then
      make_symlink "$file" "${dest_dir}/$(basename "$file")"
    else
      echo "⚠️  Warning: $(basename "$file") is not a regular file, skipping..."
    fi
  done
done

# skills はディレクトリ単位でシンボリックリンク（skills/<name>/SKILL.md 構造のため）
setup_ai_skills ~/.claude/skills "${Repo}ai/common/skills" "${Repo}ai/claude/skills"

make_symlink "${Repo}ai/claude/claude_desktop_config.json" ~/Library/Application\ Support/Claude/claude_desktop_config.json

chmod +x ~/.claude/hooks/stop-send-notification.sh
chmod +x ~/.claude/scripts/file-suggestion.sh

echo "Installing Claude tools..."

# Claude tools
'curl' -fsSL https://claude.ai/install.sh | zsh
npm install -g @sasazame/ccresume
npm install -g ccexp
npm install -g ccusage
npm install -g ccundo
pipx install claude-code-log
# 日本語設定にする
ccundo language ja

claude plugin marketplace add https://github.com/classmethod/tsumiki.git
claude plugin install tsumiki@tsumiki

setup_claude_superpowers
setup_claude_context_mode
setup_claude_rtk
setup_claude_genshijin
setup_claude_dig
setup_claude_example_skills
setup_claude_mem
setup_gsd_core_for_runtime claude install || exit 1

echo 'Claude setup and tools installation completed.'
