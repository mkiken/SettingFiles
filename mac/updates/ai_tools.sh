#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"

echo "Updating AI tools..."

# Geminiシンボリックリンクチェック
# Gemini CLIが設定ファイルを勝手に更新してしまう問題への対処
if [[ -f "${SET}mac/scripts/check_gemini_symlink.sh" ]]; then
    source "${SET}mac/scripts/check_gemini_symlink.sh"
else
    echo "⚠️  Gemini symlink check script not found"
fi

# Claude更新
echo "Updating Claude tools..."
SuperClaude update --verbose --yes

echo "AI tools update completed."
