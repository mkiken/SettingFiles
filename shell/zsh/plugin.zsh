#!/bin/zsh

# znapプラグイン設定ファイル
# znapを使用したプラグインの管理とその設定

# fzf-tab
# force zsh not to show completion menu, which allows fzf-tab to capture the unambiguous prefix
zstyle ':completion:*' menu no
# preview directory's content with eza when completing cd
zstyle ':fzf-tab:complete:cd:*' fzf-preview 'eza -1 --color=always $realpath'
# tmux uses its popup; Herdr and regular shells run fzf in the current pane.
if [[ "${HERDR_ENV:-}" != "1" && -n "${TMUX:-}" ]]; then
  zstyle ':fzf-tab:*' fzf-command ftb-tmux-popup
else
  zstyle ':fzf-tab:*' fzf-command fzf
fi

# apply to all command
zstyle ':fzf-tab:*' popup-min-size 80 12

# Wait until this many characters have been typed, before showing completions.
source_and_zcompile_if_needed "${SUBMODULE_DIR}/zsh-snap/znap.zsh"  # Start Znap

# Znap automatically enables git maintenance in each repo that it manages.
# This automatically optimizes your repos in the background, so that your git and znap commands will run faster.
zstyle ':znap:*:*' git-maintenance off

# `znap source` automatically downloads and starts your plugins.
# fzf-tab needs to be loaded after compinit, but before plugins which will wrap widgets, such as zsh-autosuggestions or fast-syntax-highlighting
znap source Aloxaf/fzf-tab
znap source zsh-users/zsh-autosuggestions
znap source z-shell/F-Sy-H

znap source jeffreytse/zsh-vi-mode
