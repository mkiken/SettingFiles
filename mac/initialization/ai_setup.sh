#!/bin/zsh

source "$(dirname "$0")/common.sh"

# for Claude
mkdir -p ~/.claude

make_symlink "${Repo}ai/common/prompt.md" ~/.claude/CLAUDE.md
for item in settings.json commands hooks; do
  make_symlink "${Repo}ai/claude/${item}" ~/.claude
done

make_symlink "${Repo}ai/claude/claude_desktop_config.json" ~/Library/Application\ Support/Claude

chmod +x ~/.claude/hooks/stop-send-notification.sh

# for Gemini
mkdir -p ~/.gemini
make_symlink "${Repo}ai/common/prompt.md" ~/.gemini/GEMINI.md

# for Cursor/Roo
mkdir -p ~/.roo/rules
make_symlink "${Repo}ai/common/prompt.md" ~/.roo/rules/.roorules

echo 'AI configurations linked.'