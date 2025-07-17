#!/bin/zsh

# powerlevel10k instant prompt configuration
# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
source_and_zcompile_if_needed "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"

# powerlevel10k theme loading
source_and_zcompile_if_needed "${BREW_PREFIX}/opt/powerlevel10k/share/powerlevel10k/powerlevel10k.zsh-theme"

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
source_and_zcompile_if_needed "${SET}shell/p10k/.p10k.zsh"

# powerlevel9k custom configurations
# 今のshellの履歴数
function my_history_count {
  echo '%i'
}
POWERLEVEL9K_CUSTOM_MY_HISTORY_COUNT="my_history_count"
POWERLEVEL9K_CUSTOM_MY_HISTORY_COUNT_BACKGROUND="grey50"
POWERLEVEL9K_CUSTOM_MY_HISTORY_COUNT_FOREGROUND="$DEFAULT_COLOR"

POWERLEVEL9K_LEFT_PROMPT_ELEMENTS=(dir vcs vi_mode)
POWERLEVEL9K_RIGHT_PROMPT_ELEMENTS=(status command_execution_time background_jobs custom_my_history_count time)

# ディレクトリ名表示
POWERLEVEL9K_SHORTEN_DIR_LENGTH=2

# zshにviのモードを表示する
# https://github.com/romkatv/powerlevel10k/issues/396
POWERLEVEL9K_VI_INSERT_MODE_STRING=INS
POWERLEVEL9K_VI_MODE_INSERT_BACKGROUND=cyan
POWERLEVEL9K_VI_MODE_INSERT_FOREGROUND=black

POWERLEVEL9K_VI_COMMAND_MODE_STRING=NOR
POWERLEVEL9K_VI_MODE_NORMAL_BACKGROUND=red
POWERLEVEL9K_VI_MODE_NORMAL_FOREGROUND=black

POWERLEVEL9K_VI_VISUAL_MODE_STRING=VIS
POWERLEVEL9K_VI_MODE_VISUAL_BACKGROUND=magenta
POWERLEVEL9K_VI_MODE_VISUAL_FOREGROUND=black

POWERLEVEL9K_VI_OVERWRITE_MODE_STRING=OVERTYPE
POWERLEVEL9K_VI_MODE_OVERWRITE_BACKGROUND=blue
POWERLEVEL9K_VI_MODE_OVERWRITE_FOREGROUND=white