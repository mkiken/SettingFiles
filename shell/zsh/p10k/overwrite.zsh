#!/usr/bin/env zsh
# vim関連設定の上書き用ファイル
# p10k.zshの設定を部分的にオーバーライドします

##############[ nvm: node.js version from nvm (https://github.com/nvm-sh/nvm) ]###############
# If set to false, hide node version if it's equal to "system".
typeset -g POWERLEVEL9K_NVM_SHOW_SYSTEM=false

###########################[ vim_shell: vim shell indicator (:sh) ]###########################
# Vim shell indicator color - カスタマイズ版
# typeset -g POWERLEVEL9K_VIM_SHELL_FOREGROUND=15    # 白文字
# typeset -g POWERLEVEL9K_VIM_SHELL_BACKGROUND=5     # マゼンタ背景

# # Custom vim shell icon - 宇宙級にクールなアイコン
# typeset -g POWERLEVEL9K_VIM_SHELL_VISUAL_IDENTIFIER_EXPANSION='🚀'

# ###########[ vi_mode: vi mode (you don't need this if you've enabled prompt_char) ]###########
# # Foreground color for all vi modes
# typeset -g POWERLEVEL9K_VI_MODE_FOREGROUND=15      # 白文字

# # Text and color for normal (command) vi mode
# # typeset -g POWERLEVEL9K_VI_COMMAND_MODE_STRING='CMD'
# typeset -g POWERLEVEL9K_VI_MODE_NORMAL_BACKGROUND=1    # 赤背景

# # Text and color for visual vi mode
# # typeset -g POWERLEVEL9K_VI_VISUAL_MODE_STRING='VIS'
# typeset -g POWERLEVEL9K_VI_MODE_VISUAL_BACKGROUND=3    # 黄背景

# # Text and color for overtype (overwrite/replace) vi mode
# # typeset -g POWERLEVEL9K_VI_OVERWRITE_MODE_STRING='OVR'
# typeset -g POWERLEVEL9K_VI_MODE_OVERWRITE_BACKGROUND=208  # オレンジ背景

# # Text and color for insert vi mode
# # typeset -g POWERLEVEL9K_VI_IkSERT_MODE_STRING='INS'
# typeset -g POWERLEVEL9K_VI_MODE_INSERT_BACKGROUND=2    # 緑背景