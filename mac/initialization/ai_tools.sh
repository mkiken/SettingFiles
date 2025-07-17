#!/bin/zsh

source "$(dirname "$0")/common.sh"

# for Claude
npm install -g @anthropic-ai/claude-code
npm install -g ccusage
npm install -g @sasazame/ccresume

claude mcp add sequential-thinking -s user -- npx -y @modelcontextprotocol/server-sequential-thinking

# for Gemini
npm install -g @google/gemini-cli

echo 'AI tools installed.'