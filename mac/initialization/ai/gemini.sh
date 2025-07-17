#!/bin/zsh

source "$(dirname "$0")/../common.sh"

echo "Setting up Gemini..."

# Gemini setup
mkdir -p ~/.gemini
make_symlink "${Repo}ai/common/prompt.md" ~/.gemini/GEMINI.md

echo "Installing Gemini tools..."

# Gemini tools
npm install -g @google/gemini-cli

echo 'Gemini setup and tools installation completed.'