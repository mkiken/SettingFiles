#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"

# Git symlinks
make_symlink "${Repo}gitfiles/.gitconfig" ~/.gitconfig
make_symlink "${Repo}gitfiles/.gitignore_global" ~/.gitignore
make_symlink "${Repo}gitfiles/.git_template" ~
make_symlink "${Repo}gitfiles/gitui" "$HOME/.config"
make_symlink "${Repo}gitfiles/gh/dash/config.yml" "$HOME/.config/gh-dash/config.yml"
make_symlink "${Repo}gitfiles/lazygit/config.yml" "$HOME/.config/lazygit/config.yml"

# Git extensions
gh extension install dlvhdr/gh-dash
gh extension install gennaro-tedesco/gh-f
gh extension install github/gh-stack

# gh stack のAIエージェント向けskill（ClaudeとCodexの両方で使うためagentごとに導入）
# --scope の既定は project でリポジトリ直下へ入ってしまうため user を明示する
# skill名を省略すると一覧表示になりインストールされないため必ず名前を渡す
# -f は再実行時に無対話で上書きするため
gh skill install github/gh-stack gh-stack --agent claude-code --scope user -f
gh skill install github/gh-stack gh-stack --agent codex --scope user -f

# Git submodules
git submodule update --init

npm install -g difit

echo 'Git configuration completed.'
