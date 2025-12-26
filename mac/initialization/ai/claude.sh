#!/bin/zsh

source "$(dirname "$0")/../../scripts/common.sh"

echo "Setting up Claude..."

# 既存の設定ファイル全部消すので先にやる
claude-code-spec-workflow setup --yes --project ~/

# Claude setup
# 共通プロンプトとClaude専用プロンプトを結合してCLAUDE.mdを生成
cat "${Repo}ai/common/prompt_base.md" \
    <(echo) <(echo) \
    "${Repo}ai/common/characters/reimu.md" \
    <(echo) <(echo) \
    "${Repo}ai/claude/claude_prompt.md" \
    > "${Repo}ai/claude/_CLAUDE.md"
echo "UPDATE ${Repo}ai/claude/_CLAUDE.md!"

make_symlink "${Repo}ai/claude/_CLAUDE.md" ~/.claude/CLAUDE.md

make_symlink "${Repo}ai/claude/ccstatusline/settings.json" ~/.config/ccstatusline/settings.json

# settings.jsonはsymlink
for item in settings.json; do
  make_symlink "${Repo}ai/claude/${item}" ~/.claude
done

# agents,commands,hooksはディレクトリ内のファイルをコピー
for item in agents commands hooks; do
  for file in "${Repo}ai/claude/${item}"/*; do
    if [[ -f "$file" ]]; then
      make_symlink "$file" ~/.claude/${item}/$(basename "$file")
    else
      echo "⚠️  Warning: $(basename "$file") is not a regular file, skipping..."
    fi
  done
done

make_symlink "${Repo}ai/claude/claude_desktop_config.json" ~/Library/Application\ Support/Claude/claude_desktop_config.json

chmod +x ~/.claude/hooks/stop-send-notification.sh

echo "Installing Claude tools..."

# Claude tools
npm install -g @anthropic-ai/claude-code
npm install -g @pimzino/claude-code-spec-workflow
npm install -g @sasazame/ccresume
npm install -g ccexp
npm install -g ccusage
npm install -g ccstatusline@latest
pipx install SuperClaude && SuperClaude install
pipx install claude-code-log

claude mcp add sequential-thinking -s user -- npx -y @modelcontextprotocol/server-sequential-thinking
claude mcp add context7 -s user -- npx -y @upstash/context7-mcp
claude mcp add serena --scope "user" -- uvx --from git+https://github.com/oraios/serena serena start-mcp-server --context ide-assistant
claude mcp add gitmcp -s user -- npx mcp-remote https://gitmcp.io/docs


echo 'Claude setup and tools installation completed.'