#!/bin/zsh
# Mac specific aliases

# エディタ関連
alias v='code'
alias cu='cursor'

# ls系（ezaを使用）
alias ls='eza --time-style=long-iso -g'
alias tree='eza -T --color=always'
alias la='ls -a'
alias ll='la -lm --git'

# 代替コマンド
alias df='duf'
alias top='glances'
alias wget='aria2c'
alias curl='https'
alias cat='bat --style=plain'
alias du='dust'

# fd関連
alias fda='fd -HI'
alias fdh='fd -H'
alias fdi='fd -I'
alias fdad='fda --type=d'
alias fdhd='fdh --type=d'
alias fdid='fdi --type=d'

# Mac固有
alias pg='sudo purge'
alias cask='brew cask'
alias karabiner-export='/Applications/Karabiner.app/Contents/Library/bin/karabiner export > ${SET}mac/karabiner-setting.sh'
alias karabiner-import='sh ${SET}mac/karabiner-setting.sh'
alias rm='trash'
alias allfile='defaults write com.apple.finder AppleShowAllFiles'

# pbcopy/pbpaste
alias -g pc='tee >(pbcopy)'
alias -g C='| pc'
alias -g pp='pbpaste'