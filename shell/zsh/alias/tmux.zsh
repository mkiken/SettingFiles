#!/bin/zsh
# tmux aliases

alias tm='tmux'
alias tmks='tm kill-server'

# tmuxで新しくペインを作成してコマンドを実行
# 水平分割
function sp() {
  _sp "$*"
}
# 水平分割してless
function spl() {
  _sp "$* | less"
}

function _sp() {
  tmux split-window "$*"
}

# 垂直分割
function vsp() {
  _vsp "$*"
}

# 垂直分割してless
function vspl() {
  _vsp "$* | less"
}

function _vsp() {
  tmux split-window -h "$*"
}