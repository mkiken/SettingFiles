#!/bin/bash

# 「The default interactive shell is now zsh」のwarning抑制
export BASH_SILENCE_DEPRECATION_WARNING=1

[[ "$TERM_PROGRAM" == "vscode" ]] && . "$(code --locate-shell-integration-path bash)"