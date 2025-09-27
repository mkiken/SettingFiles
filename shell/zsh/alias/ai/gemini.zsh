#!/bin/zsh

alias update-gemini='npm update -g @google/gemini-cli'

gm() {
    no_notify gemini "$@"
}