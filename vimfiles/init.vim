"NeoVim Settings for CUI

if !exists('g:setting_files_path')
  let g:setting_files_path = $HOME.'/Desktop/repository/SettingFiles' | lockvar! setting_files_path
endif

" http://stackoverflow.com/questions/840900/vim-sourcing-based-on-a-string/841025#841163
exec 'source ' .  g:setting_files_path . '/vimfiles/.vimrc.common'
