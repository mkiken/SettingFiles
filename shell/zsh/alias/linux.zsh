#!/bin/zsh
# Linux specific aliases

alias ls='ls --color=auto'
function vi(){
    gvim -f --remote-tab-silent "${@}" &
}