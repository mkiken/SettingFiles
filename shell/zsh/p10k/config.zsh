#!/bin/zsh

# 起動時に文字出力があるとwarningで出るのを抑える
typeset -g POWERLEVEL9K_INSTANT_PROMPT=off

source_and_zcompile_if_needed "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"

# powerlevel10k theme loading
source_and_zcompile_if_needed "${BREW_PREFIX}/opt/powerlevel10k/share/powerlevel10k/powerlevel10k.zsh-theme"

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
source_and_zcompile_if_needed "${SET}shell/zsh/p10k/.p10k.zsh"

# vim関連設定の上書き読み込み
source_and_zcompile_if_needed "${SET}shell/zsh/p10k/overwrite.zsh"
