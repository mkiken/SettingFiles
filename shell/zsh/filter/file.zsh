#!/bin/zsh

alias fls='ls -aR | filter --preview "bat --color=always --style=header,grid {}"'
alias ffind='fda | filter --preview "bat --color=always --style=header,grid {}"'
alias fps='ps aux | filter'
alias fkill='ps ax | filter | awk "{ print $1 }" | xargs kill'
alias fopen='filter_find_command open'
alias fless='filter_find_command less'
alias fnv='filter_find_command nvim'

function fcat(){
  cat -n $@ | filter
}

# findの結果をfilter toolで絞ってコマンドを実行する
function filter_find_command(){
  local cmd="$(ffind)"
  save_history "$@" $cmd
}