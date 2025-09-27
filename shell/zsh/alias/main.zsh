#!/bin/zsh
# Main alias loader - loads all alias files

# OSごとのalias読み込み
case "${OSTYPE}" in
  darwin*)
    source_and_zcompile_if_needed "${SET}shell/zsh/alias/mac.zsh"
    ;;
  linux*)
    source_and_zcompile_if_needed "${SET}shell/zsh/alias/linux.zsh"
    ;;
esac

# 共通alias読み込み
source_and_zcompile_if_needed "${SET}shell/zsh/alias/other.zsh"
source_and_zcompile_if_needed "${SET}shell/zsh/alias/ai/claude.zsh"
source_and_zcompile_if_needed "${SET}shell/zsh/alias/ai/gemini.zsh"
source_and_zcompile_if_needed "${SET}shell/zsh/alias/git.zsh"
source_and_zcompile_if_needed "${SET}shell/zsh/alias/gh.zsh"
source_and_zcompile_if_needed "${SET}shell/zsh/alias/tmux.zsh"
source_and_zcompile_if_needed "${SET}shell/zsh/alias/docker.zsh"
source_and_zcompile_if_needed "${SET}shell/zsh/alias/notification.zsh"