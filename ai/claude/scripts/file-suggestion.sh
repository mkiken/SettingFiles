#!/bin/bash
query=$(cat | jq -r '.query')
cd "$CLAUDE_PROJECT_DIR"
fd | fzf --filter="$query" | head -20
