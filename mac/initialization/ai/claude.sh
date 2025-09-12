#!/bin/zsh

source "$(dirname "$0")/../common.sh"

echo "Setting up Claude..."

# Claude setup
make_symlink "${Repo}ai/common/prompt.md" ~/.claude/CLAUDE.md
make_symlink "${Repo}ai/claude/statusline-custom.sh" ~/.claude/statusline-custom.sh
for item in settings.json agents commands hooks; do
  make_symlink "${Repo}ai/claude/${item}" ~/.claude
done

make_symlink "${Repo}ai/claude/claude_desktop_config.json" ~/Library/Application\ Support/Claude/claude_desktop_config.json
make_symlink "~/Library/CloudStorage/Dropbox/Obsidian/.obsidian/plugins/mcp-tools/bin/mcp-server" /usr/local/bin

chmod +x ~/.claude/hooks/stop-send-notification.sh

echo "Installing Claude tools..."

# Claude tools
npm install -g @anthropic-ai/claude-code
npm install -g @pimzino/claude-code-spec-workflow
npm install -g @sasazame/ccresume
npm install -g ccexp
npm install -g ccusage
pipx install SuperClaude && SuperClaude install
pipx install claude-code-log

claude mcp add sequential-thinking -s user -- npx -y @modelcontextprotocol/server-sequential-thinking
claude mcp add context7 -s user -- npx -y @upstash/context7-mcp
claude mcp add serena --scope "user" -- uvx --from git+https://github.com/oraios/serena serena start-mcp-server --context ide-assistant
claude mcp add gitmcp -s user -- npx mcp-remote https://gitmcp.io/docs
claude mcp add obsidian -s user -- npx -y mcp-obsidian "$HOME/Library/CloudStorage/Dropbox/Obsidian"

claude-code-spec-workflow


echo 'Claude setup and tools installation completed.'