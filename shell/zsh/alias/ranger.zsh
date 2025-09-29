#!/bin/zsh

function ranger() {
    if [ -z "${RANGER_LEVEL}" ]; then
        no_notify pipx run --spec ranger-fm ranger "$@"
    else
        exit
    fi
}

function ranger-cd() {
    if [ -z "${RANGER_LEVEL}" ]; then
        # [linux - How to exit the Ranger file explorer back to command prompt but keep the current directory? - Super User](https://superuser.com/questions/1043806/how-to-exit-the-ranger-file-explorer-back-to-command-prompt-but-keep-the-current/1043815#1043815)
        no_notify pipx run --spec ranger-fm ranger --choosedir=$HOME/.rangerdir; LASTDIR=`cat $HOME/.rangerdir`; cd "$LASTDIR"
    else
        exit
    fi
}

alias ra='ranger'
alias rac='ranger-cd'