#!/bin/zsh

source "$(dirname "$0")/common.sh"

make_symlink "${Repo}gitfiles/.gitconfig" ~/.gitconfig

make_symlink "${Repo}gitfiles/.gitignore_global" ~/.gitignore

make_symlink "${Repo}gitfiles/.git_template" ~

mkdir -p ~/.config

make_symlink "${Repo}ranger" ~/.config

mkdir -p ~/.config/karabiner
make_symlink "${Repo}mac/karabiner.json" ~/.config/karabiner

make_symlink "${Repo_shell}.zshrc" ~/.zshrc

make_symlink "${Repo}gitfiles/gitui" "$HOME/.config"
make_symlink "${Repo}.tmux.conf" ~/.tmux.conf

make_symlink "${Repo}.ideavimrc" ~/.ideavimrc

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

mkdir -p ~/.roo/rules
make_symlink "${Repo}ai/common/prompt.md" ~/.roo/rules/.roorules

echo 'symbolic links created.'