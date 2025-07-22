#!/bin/bash

# 「The default interactive shell is now zsh」のwarning抑制
export BASH_SILENCE_DEPRECATION_WARNING=1

# Load common Claude aliases
# より確実にファイルの場所を取得してsource
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}" || echo "${BASH_SOURCE[0]}")")" && pwd)"
source "${SCRIPT_DIR}/../common/alias/claude.sh"

[[ "$TERM_PROGRAM" == "vscode" ]] && . "$(code --locate-shell-integration-path bash)"