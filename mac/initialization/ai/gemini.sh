#!/bin/zsh

source "$(dirname "$0")/../common.sh"

echo "Setting up Gemini..."

# Gemini setup
cat "${Repo}ai/common/prompt_base.md" > "${Repo}ai/gemini/_GEMINI.md"
echo "UPDATE ${Repo}ai/gemini/_GEMINI.md!"

make_symlink "${Repo}ai/gemini/_GEMINI.md" ~/.gemini/GEMINI.md

echo "Installing Gemini tools..."

# Gemini tools
npm install -g @google/gemini-cli

echo 'Gemini setup and tools installation completed.'