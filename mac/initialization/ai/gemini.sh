#!/bin/zsh

source "$(dirname "$0")/../../scripts/common.sh"

echo "Setting up Gemini..."

setup_ai_mcp install
setup_ai_pr_tools

# jqコマンドの確認
if ! command -v jq &> /dev/null; then
    echo "Error: jq is not installed. Please install it with 'brew install jq'"
    exit 1
fi

# Gemini setup
echo "UPDATE ${Repo}ai/gemini/_GEMINI.md!"

# JSONマージ処理
echo "Merging MCP configuration into settings.json..."
jq -s '.[0] * .[1]' "${Repo}ai/gemini/settings.json" "${Repo}ai/common/mcp.json" > "${Repo}ai/gemini/settings.json.tmp"
mv "${Repo}ai/gemini/settings.json.tmp" "${Repo}ai/gemini/settings.json"
echo "MCP configuration merged successfully!"

make_symlink "${Repo}ai/gemini/_GEMINI.md" ~/.gemini/GEMINI.md
make_symlink "${Repo}ai/common" ~/.gemini/common

# ローカルMCP設定があれば一時ファイルにマージしてコピー
LOCAL_MCP="${Repo}ai/common/mcp.local.json"
if [[ -f "$LOCAL_MCP" ]]; then
    echo "Found local MCP config, merging..."
    MERGED_TMP=$(mktemp)
    jq -s '.[0] * .[1]' "${Repo}ai/gemini/settings.json" "$LOCAL_MCP" > "$MERGED_TMP"
    smart_merge_json "$MERGED_TMP" ~/.gemini/settings.json
    rm -f "$MERGED_TMP"
else
    smart_merge_json "${Repo}ai/gemini/settings.json" ~/.gemini/settings.json
fi

# commands,hooksなどはディレクトリ内のファイルをコピー
for item in agents commands hooks policies; do
  mkdir -p ~/.gemini/${item}
  for file in "${Repo}ai/gemini/${item}"/*; do
    if [[ "$(basename "$file")" == test_*.py ]]; then
      continue
    elif [[ -f "$file" ]]; then
      make_symlink "$file" ~/.gemini/${item}/$(basename "$file")
    elif [[ -d "$file" ]]; then
      continue
    else
      echo "⚠️  Warning: $(basename "$file") is not a regular file, skipping..."
    fi
  done
done

# skills はディレクトリ単位でシンボリックリンク（skills/<name>/SKILL.md 構造のため）
setup_ai_skills ~/.gemini/skills "${Repo}ai/common/skills" "${Repo}ai/gemini/skills"

chmod +x ~/.gemini/hooks/notification.sh

echo 'Gemini setup completed.'
