#!/usr/bin/env zsh
# vim関連設定の上書き用ファイル
# p10k.zshの設定を部分的にオーバーライドします

##############[ nvm: node.js version from nvm (https://github.com/nvm-sh/nvm) ]###############
# If set to false, hide node version if it's equal to "system".
typeset -g POWERLEVEL9K_NVM_SHOW_SYSTEM=false

###########################[ vim_shell: vim shell indicator (:sh) ]###########################

# vim shellはアイコン表示しない
typeset -g POWERLEVEL9K_VIM_SHELL_VISUAL_IDENTIFIER_EXPANSION=''

# ###########[ vi_mode: vi mode (you don't need this if you've enabled prompt_char) ]###########

# # Text and color for normal (command) vi mode
typeset -g POWERLEVEL9K_VI_COMMAND_MODE_STRING='' # vimアイコン
typeset -g POWERLEVEL9K_VI_MODE_NORMAL_BACKGROUND=1 # 赤

# # Text and color for visual vi mode
typeset -g POWERLEVEL9K_VI_VISUAL_MODE_STRING='' # vimアイコン
typeset -g POWERLEVEL9K_VI_MODE_VISUAL_BACKGROUND=4 # 青

# # Text and color for overtype (overwrite/replace) vi mode
typeset -g POWERLEVEL9K_VI_OVERWRITE_MODE_STRING='' # vimアイコン

# # Text and color for insert vi mode
typeset -g POWERLEVEL9K_VI_INSERT_MODE_STRING='' # vimアイコン
typeset -g POWERLEVEL9K_VI_MODE_INSERT_BACKGROUND=2 # 緑 設定しないとなぜか黒くなる