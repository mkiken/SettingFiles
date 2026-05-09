#!/bin/zsh

source "$(dirname "$0")/../../scripts/common.sh"

echo "Setting up Claude..."

setup_ai_mcp install

# Claude setup
echo "UPDATE ${Repo}ai/claude/_CLAUDE.md!"

make_symlink "${Repo}ai/claude/_CLAUDE.md" ~/.claude/CLAUDE.md

make_symlink "${Repo}ai/claude/statusline-command.sh" ~/.claude/statusline-command.sh

for item in settings.json; do
  smart_merge_json "${Repo}ai/claude/${item}" ~/.claude/${item}
done

# agents,commands,hooksはディレクトリ内のファイルをコピー
for item in agents commands hooks; do
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
skills_dest=~/.claude/skills
mkdir -p "$skills_dest"
for skill_dir in "${Repo}ai/claude/skills"/*/; do
  if [[ -d "$skill_dir" ]]; then
    skill_name=$(basename "$skill_dir")
    make_symlink "$skill_dir" "${skills_dest}/${skill_name}"
  fi
done

make_symlink "${Repo}ai/claude/claude_desktop_config.json" ~/Library/Application\ Support/Claude/claude_desktop_config.json

chmod +x ~/.claude/hooks/stop-send-notification.sh

echo "Installing Claude tools..."

# Claude tools
'curl' -fsSL https://claude.ai/install.sh | zsh
npm install -g @sasazame/ccresume
npm install -g ccexp
npm install -g ccusage
npm install -g ccundo
pipx install SuperClaude && SuperClaude install
pipx install claude-code-log
# 日本語設定にする
ccundo language ja

claude mcp add sequential-thinking -s user -- zsh -c 'exec "$HOME/.config/ai-mcp/bin/sequential-thinking"'
claude mcp add context7 -s user -- zsh -c 'exec "$HOME/.config/ai-mcp/bin/context7"'
claude mcp add serena --scope "user" -- uvx --from git+https://github.com/oraios/serena serena start-mcp-server --context ide-assistant
claude mcp add gitmcp -s user -- zsh -c 'exec "$HOME/.config/ai-mcp/bin/gitmcp" https://gitmcp.io/docs'

claude plugin marketplace add https://github.com/classmethod/tsumiki.git
claude plugin install tsumiki@tsumiki

claude plugin marketplace add sawyerhood/dev-browser
# claude pluginコマンドだとエラーになるため、直接clコマンドでインストール
claude -p "/plugin install dev-browser@sawyerhood/dev-browser"

cd ~/
npx cc-sdd@latest --claude-skills --lang ja
cd $OLDPWD

echo 'Claude setup and tools installation completed.'
