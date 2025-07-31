#!/bin/zsh

source "$(dirname "$0")/../common.sh"

echo "Setting up Claude..."

# Claude setup
mkdir -p ~/.claude

make_symlink "${Repo}ai/common/prompt.md" ~/.claude/CLAUDE.md
for item in settings.json agents commands hooks; do
  make_symlink "${Repo}ai/claude/${item}" ~/.claude
done

make_symlink "${Repo}ai/claude/claude_desktop_config.json" ~/Library/Application\ Support/Claude

chmod +x ~/.claude/hooks/stop-send-notification.sh

echo "Installing Claude tools..."

# Claude tools
npm install -g @anthropic-ai/claude-code
npm install -g ccusage
npm install -g @sasazame/ccresume

claude mcp add sequential-thinking -s user -- npx -y @modelcontextprotocol/server-sequential-thinking
claude mcp add context7 -s user -- npx -y @upstash/context7-mcp
claude mcp add serena --scope "user" -- uvx --from git+https://github.com/oraios/serena serena start-mcp-server --context ide-assistant

echo 'Claude setup and tools installation completed.'