#!/bin/zsh

source "$(dirname "$0")/../../scripts/common.sh"

echo "Setting up Gemini..."

# jqコマンドの確認
if ! command -v jq &> /dev/null; then
    echo "Error: jq is not installed. Please install it with 'brew install jq'"
    exit 1
fi

# Gemini setup
cat "${Repo}ai/common/prompt_base.md" \
    <(echo) <(echo) \
    "${Repo}ai/common/characters/nyaruko.md" \
    <(echo) <(echo) \
    "${Repo}ai/gemini/gemini_prompt.md" \
    > "${Repo}ai/gemini/_GEMINI.md"
echo "UPDATE ${Repo}ai/gemini/_GEMINI.md!"

# JSONマージ処理
echo "Merging MCP configuration into settings.json..."
jq -s '.[0] * .[1]' "${Repo}ai/gemini/settings.json" "${Repo}ai/common/mcp.json" > "${Repo}ai/gemini/settings.json.tmp"
mv "${Repo}ai/gemini/settings.json.tmp" "${Repo}ai/gemini/settings.json"
echo "MCP configuration merged successfully!"

make_symlink "${Repo}ai/gemini/_GEMINI.md" ~/.gemini/GEMINI.md

# ローカルMCP設定があれば一時ファイルにマージしてコピー
LOCAL_MCP="${Repo}ai/common/mcp.local.json"
if [[ -f "$LOCAL_MCP" ]]; then
    echo "Found local MCP config, merging..."
    MERGED_TMP=$(mktemp)
    jq -s '.[0] * .[1]' "${Repo}ai/gemini/settings.json" "$LOCAL_MCP" > "$MERGED_TMP"
    smart_copy "$MERGED_TMP" ~/.gemini/settings.json
    rm -f "$MERGED_TMP"
else
    smart_copy "${Repo}ai/gemini/settings.json" ~/.gemini/settings.json
fi

# commands,hooksはディレクトリ内のファイルをコピー
for item in commands hooks; do
  mkdir -p ~/.gemini/${item}
  for file in "${Repo}ai/gemini/${item}"/*; do
    if [[ -f "$file" ]]; then
      make_symlink "$file" ~/.gemini/${item}/$(basename "$file")
    else
      echo "⚠️  Warning: $(basename "$file") is not a regular file, skipping..."
    fi
  done
done

chmod +x ~/.gemini/hooks/notification.sh

echo "Installing Gemini tools..."

# Gemini tools
npm install -g @google/gemini-cli

pipx install SuperGemini && SuperGemini install --verbose --yes

echo 'Gemini setup and tools installation completed.'