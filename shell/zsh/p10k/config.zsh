#!/usr/local/bin/zsh

source_and_zcompile_if_needed "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"

# powerlevel10k theme loading
source_and_zcompile_if_needed "${BREW_PREFIX}/opt/powerlevel10k/share/powerlevel10k/powerlevel10k.zsh-theme"

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
source_and_zcompile_if_needed "${SET}shell/zsh/p10k/.p10k.zsh"
