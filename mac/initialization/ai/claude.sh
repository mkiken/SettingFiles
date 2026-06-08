#!/bin/zsh

source "$(dirname "$0")/../../scripts/common.sh"

echo "Setting up Claude..."

setup_ai_mcp install
setup_ai_pr_tools

# Claude setup
echo "UPDATE ${Repo}ai/claude/_CLAUDE.md!"

make_symlink "${Repo}ai/claude/_CLAUDE.md" ~/.claude/CLAUDE.md

make_symlink "${Repo}ai/claude/statusline-command.sh" ~/.claude/statusline-command.sh

for item in settings.json; do
  smart_merge_json "${Repo}ai/claude/${item}" ~/.claude/${item}
done

# agents,commands,hooks,scripts はディレクトリ内のファイルをシンボリックリンク
for item in agents commands hooks scripts; do
  if [[ "$item" == "commands" ]]; then
    dest_dir=~/.claude/commands/my
  else
    dest_dir=~/.claude/${item}
  fi

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

claude mcp add sequential-thinking -s user -- zsh -c 'exec "$HOME/.config/ai-mcp/bin/sequential-thinking"'
claude mcp add context7 -s user -- zsh -c 'exec "$HOME/.config/ai-mcp/bin/context7"'
claude mcp add serena --scope "user" -- uvx --from git+https://github.com/oraios/serena serena start-mcp-server --context ide-assistant

claude plugin marketplace add https://github.com/classmethod/tsumiki.git
claude plugin install tsumiki@tsumiki

claude plugin marketplace add sawyerhood/dev-browser
# claude pluginコマンドだとエラーになるため、直接clコマンドでインストール
claude -p "/plugin install dev-browser@sawyerhood/dev-browser"

echo 'Claude setup and tools installation completed.'
