"NeoVim Settings for CUI
if !exists('g:setting_files_path')
  let g:setting_files_path = $HOME.'/Desktop/repository/SettingFiles' | lockvar! setting_files_path
  let g:vim_dir_path = g:setting_files_path . '/vimfiles' | lockvar! vim_dir_path
endif

" http://stackoverflow.com/questions/840900/vim-sourcing-based-on-a-string/841025#841163
exec 'source ' .  g:setting_files_path . '/vimfiles/.vimrc.common'

let s:dein_dir = g:vim_dir_path . '/dein/nvim'
" プラグインが実際にインストールされるディレクトリ
let s:dein_bundle_dir = s:dein_dir . '/bundle'
" dein.vim 本体
let s:dein_repo_dir = s:dein_bundle_dir . '/repos/github.com/Shougo/dein.vim'

" dein.vim がなければ github から落としてくる
if &runtimepath !~# '/dein.vim'
  if !isdirectory(s:dein_repo_dir)
    execute '!git clone https://github.com/Shougo/dein.vim' s:dein_repo_dir
  endif
  execute 'set runtimepath^=' . fnamemodify(s:dein_repo_dir, ':p')
endif

" 設定開始
if dein#load_state(s:dein_bundle_dir)
  call dein#begin(s:dein_bundle_dir)

  " プラグインリストを収めた TOML ファイル
  " 予め TOML ファイル（後述）を用意しておく
  let s:toml      = s:dein_dir . '/dein.toml'
  " let s:lazy_toml = s:dein_dir . '/dein_lazy.toml'

  " TOML を読み込み、キャッシュしておく
  call dein#load_toml(s:toml,      {'lazy': 0})
  " call dein#load_toml(s:lazy_toml, {'lazy': 1})

  " 設定終了
  call dein#end()
  call dein#save_state()
endif

" もし、未インストールものものがあったらインストール
if dein#check_install()
  call dein#install()
endif


" Theme設定
" syntax enable
syntax on
" colorscheme codeschool
" GUI設定
" if (has("termguicolors"))
 " set termguicolors
" endif
" colorscheme OceanicNext
" colorscheme kalisi

