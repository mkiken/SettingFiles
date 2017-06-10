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
  let s:lazy_toml = s:dein_dir . '/dein_lazy.toml'

  " TOML を読み込み、キャッシュしておく
  call dein#load_toml(s:toml,      {'lazy': 0})
  call dein#load_toml(s:lazy_toml, {'lazy': 1})

  " 設定終了
  call dein#end()
  call dein#save_state()
endif

" もし、未インストールものものがあったらインストール
if dein#check_install()
  call dein#install()
endif

" for NERDCommenter
filetype plugin on


" Theme設定
" syntax enable
syntax on
" GUI設定
" if (has("termguicolors"))
 " set termguicolors
" endif
colorscheme OceanicNext
" colorscheme kalisi

" キーバインド
" NEDRCommenter
let NERDSpaceDelims = 1
nmap ,, <Plug>NERDCommenterToggle
vmap ,, <Plug>NERDCommenterToggle

" vimrcをリロード
" http://whileimautomaton.net/2008/07/20150335
" nnoremap <Space>s  :<C-u>source $VIMRC<Return>
" nnoremap <Leader>s  :<C-u>source g:vim_dir_path . '/init.vim' <Return>
nnoremap <Leader>s  :<C-u>source ~/.config/nvim/init.vim <Return>
" command! ReloadVimrc  :source ~/.vimrc

" Use deoplete.
let g:deoplete#enable_at_startup = 1

" Denite
nnoremap    [denite]   <Nop>
nmap    <Leader>d [denite]
nnoremap [denite]u  :<C-u>Denite -no-split<Space>
nnoremap <silent> [denite]t :<C-u>Denite buffer -no-quit<CR>
nnoremap <silent> [denite]c :<C-u>Denite colorscheme -auto-preview<CR>
nnoremap <silent> [denite]m :<C-u>Denite file_mru<CR>
nnoremap <silent> [denite]d :<C-u>DeniteBufferDir file<CR>
nnoremap <silent> [denite]r :<C-u>Denite file_rec<CR>
nnoremap <silent> [denite]p :<C-u>Denite file_rec:!<CR>
nnoremap <silent> [denite]f :<C-u>DeniteBufferDir -buffer-name=files file<CR>
nnoremap <silent> [denite]y :<C-u>Denite neoyank<CR>
" nnoremap <silent> [denite]o :<C-u>Denite -vertical -winwidth=40<Space>outline<CR>
" http://d.hatena.ne.jp/osyo-manga/20130617/1371468776
" nnoremap <silent> [denite]v :<C-u>Denite output:let<CR>
" nnoremap <silent> [denite]g :<C-u>Denite<Space>giti<CR>
" vimprocがいるらしい http://mba-hack.blogspot.jp/2013/03/denitevim.html
nnoremap <silent> [denite]g :<C-u>Denite grep:. -buffer-name=search-buffer -no-quit<CR>
nnoremap <silent> [denite]q :Denite -resume<CR>
" nnoremap <silent> [denite]/ :<C-u>Denite -buffer-name=search line -start-insert -no-quit<CR>
nnoremap <silent> [denite]/ :<C-u>Denite -buffer-name=search -auto-resize line<CR>
nnoremap <silent> [denite]h :<C-u>Denite help<CR>
nnoremap <silent> [denite]l :<C-u>Denite line<CR>

" デフォルトが # なのがちょっと落ち着かないので>へ変更
call denite#custom#option('default', 'prompt', '>')

" denite/insert モードのときは，C- で移動できるようにする
call denite#custom#map('insert', "<C-j>", '<denite:move_to_next_line>')
call denite#custom#map('insert', "<C-k>", '<denite:move_to_previous_line>')

" tabopen や vsplit のキーバインドを割り当て
call denite#custom#map('insert', "<C-t>", '<denite:do_action:tabopen>')
call denite#custom#map('insert', "<C-v>", '<denite:do_action:vsplit>')
call denite#custom#map('insert', "<C-s>", '<denite:do_action:split>')
call denite#custom#map('normal', "t", '<denite:do_action:tabopen>')
call denite#custom#map('normal', "v", '<denite:do_action:vsplit>')
call denite#custom#map('normal', "s", '<denite:do_action:split>')
