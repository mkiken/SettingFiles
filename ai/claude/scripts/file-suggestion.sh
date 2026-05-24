#!/bin/bash
# https://dev.classmethod.jp/articles/shuntaka-claude-code-file-fzf-search/
query=$(cat | jq -r '.query')
cd "$CLAUDE_PROJECT_DIR"
fd | fzf --filter="$query" | head -20
