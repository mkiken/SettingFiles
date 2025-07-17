#!/bin/zsh

# znapプラグイン設定ファイル
# znapを使用したプラグインの管理とその設定

# fzf-tab
# force zsh not to show completion menu, which allows fzf-tab to capture the unambiguous prefix
zstyle ':completion:*' menu no
# preview directory's content with eza when completing cd
zstyle ':fzf-tab:complete:cd:*' fzf-preview 'eza -1 --color=always $realpath'
# we provide a script ftb-tmux-popup to make full use of it's "popup" feature.
zstyle ':fzf-tab:*' fzf-command ftb-tmux-popup

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

if ! $IS_VSCODE && ! $IS_WARP; then
  # VSCodeでは「zsh-notify: unsupported environment」となる
  znap source marzocchi/zsh-notify
fi
znap source jeffreytse/zsh-vi-mode

# zsh-notifyの設定
zstyle ':notify:*' command-complete-timeout 6
zstyle ':notify:*' always-notify-on-failure no # 失敗時に毎回通知しないようにする