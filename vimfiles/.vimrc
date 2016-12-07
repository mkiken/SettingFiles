"Vim Settings for CUI

" https://github.com/kana/vim-smartinput/issues/67
" これが原因かcabbrev展開されない・・・？

cabbrev a Ag
" cabbrev t TagbarCurrentTag
" cabbrev t <c-r>=(getcmdtype()==':' && getcmdpos()==1 ? 'TagbarCurrentTag' : 't')<CR>
command! Ga :call Gadd()
command! Gb Gblame
command! Gc Gcommit
command! Gd Gdiff
command! Gr Gread
command! Gs Gstatus
command! Bo BufOnly

if !exists('g:setting_files_path')
  let g:setting_files_path = $HOME.'/Desktop/repository/SettingFiles' | lockvar! setting_files_path
  let g:vim_dir_path = g:setting_files_path . '/vimfiles' | lockvar! vim_dir_path
endif

" MacVimデフォルトのカラースキームを読み込まないようにする
let g:macvim_skip_colorscheme=1

" http://stackoverflow.com/questions/840900/vim-sourcing-based-on-a-string/841025#841163
exec 'source ' .  g:vim_dir_path . '/.vimrc.common'

" cnoremap <CR> <Plug>(anzu-update-search-status)<Plug>(anzu-echo-search-status)<CR>


" ##################################
" ###   Plugins
" ##################################

" http://lambdalisue.hatenablog.com/entry/2015/12/25/000046
" 不要なデフォルトプラグインを止める
let g:loaded_gzip              = 1
let g:loaded_tar               = 1
let g:loaded_tarPlugin         = 1
let g:loaded_zip               = 1
let g:loaded_zipPlugin         = 1
let g:loaded_rrhelper          = 1
let g:loaded_2html_plugin      = 1
let g:loaded_vimball           = 1
let g:loaded_vimballPlugin     = 1
let g:loaded_getscript         = 1
let g:loaded_getscriptPlugin   = 1
let g:loaded_netrw             = 1
let g:loaded_netrwPlugin       = 1
let g:loaded_netrwSettings     = 1
let g:loaded_netrwFileHandlers = 1

 if has('vim_starting')
   if &compatible
     set nocompatible               " Be iMproved
   endif
 endif

" どこか最初の方に書いておく
" http://qiita.com/delphinus/items/00ff2c0ba972c6e41542#on_source-%E3%83%95%E3%83%83%E3%82%AF%E3%81%AE%E8%A8%AD%E5%AE%9A%E6%96%B9%E6%B3%95%E3%81%8C%E5%A4%89%E3%82%8F%E3%81%A3%E3%81%9F
augroup MyAutoCmd
  autocmd!
augroup END


let s:dein_dir = g:vim_dir_path . '/dein'
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

if 1
" if dein#tap('unite.vim')
  " 実行すべき関数
  " function! s:unite_on_source() abort
    " unite.vimの設定
    " ウィンドウを水平分割なら下に、垂直分割なら右に開く
    let g:unite_split_rule = 'botright'
    " vinarise
    " let g:vinarise_enable_auto_detect = 1
    " ESCキーを2回押すと終了する
    au FileType unite nnoremap <silent> <buffer> <ESC><ESC> :q<CR>
    au FileType unite inoremap <silent> <buffer> <ESC><ESC> <ESC>:q<CR>

    "インサートモードで開始
    let g:unite_enable_start_insert = 1
    "最近開いたファイル履歴の保存数
    let g:unite_source_file_mru_limit = 50
    "file_mruの表示フォーマットを指定。空にすると表示スピードが高速化される
    let g:unite_source_file_mru_filename_format = ''

    "uniteを開いている間のキーマッピング
    autocmd vimrc FileType unite call s:unite_my_settings()
    function! s:unite_my_settings()"{{{
	    "ESCでuniteを終了
	    " nmap <buffer> <ESC> <Plug>(unite_exit)
	    "入力モードのときjjでノーマルモードに移動
	    " imap <buffer> jj <Plug>(unite_insert_leave)
	    "入力モードのときctrl+wでバックスラッシュも削除
	    " imap <buffer> <C-w> <Plug>(unite_delete_backward_path)
	    "ctrl+jで縦に分割して開く
	    nnoremap <silent> <buffer> <expr> s unite#do_action('split')
	    inoremap <silent> <buffer> <expr> <C-s> unite#do_action('split')
	    "ctrl+jで横に分割して開く
	    nnoremap <silent> <buffer> <expr> v unite#do_action('vsplit')
	    inoremap <silent> <buffer> <expr> <C-v> unite#do_action('vsplit')
	    "ctrl+oでその場所に開く
	    nnoremap <silent> <buffer> <expr> o unite#do_action('open')
	    inoremap <silent> <buffer> <expr> <C-o> unite#do_action('open')
	    "ctrl+tでタブで開く
	    nnoremap <silent> <buffer> <expr> t unite#do_action('tabopen')
	    inoremap <silent> <buffer> <expr> <C-t> unite#do_action('tabopen')
	    "ctrl+aで上部に開く
	    nnoremap <silent> <buffer> <expr> a unite#do_action('above')
	    inoremap <silent> <buffer> <expr> <C-a> unite#do_action('above')
	    "ctrl+bで下部に開く
	    nnoremap <silent> <buffer> <expr> b unite#do_action('below')
	    inoremap <silent> <buffer> <expr> <C-b> unite#do_action('below')
	    "ctrl+rで下部に開く
	    nnoremap <silent> <buffer> <expr> r unite#do_action('right')
	    inoremap <silent> <buffer> <expr> <C-r> unite#do_action('right')
	    "ctrl+lで下部に開く
	    nnoremap <silent> <buffer> <expr> l unite#do_action('left')
	    inoremap <silent> <buffer> <expr> <C-l> unite#do_action('left')
	    "ctrl+bでブックマーク
	    nnoremap <silent> <buffer> <expr> b unite#do_action('bookmark')
	    inoremap <silent> <buffer> <expr> <C-b> unite#do_action('bookmark')
    endfunction"}}}

  " endfunction
" echom g:dein#name
  " g:dein#name にはプラグイン名が入る
  " execute 'autocmd MyAutoCmd User' 'dein#source#' . g:dein#name
  " execute 'autocmd MyAutoCmd User' 'dein#source#unite.vim'
        " \ 'call s:unite_on_source()'
  " call dein#set_hook('unite.vim', 'hook_post_source', function('s:unite_on_source'))
endif

" tagbar
  nn <silent> <leader>t :TagbarToggle<CR>
  let g:tagbar_left = 1

 " ホームポジションに近いキーを使う
" http://blog.remora.cx/2012/08/vim-easymotion.html
"let g:EasyMotion_keys='hjklasdfgyuiopqwertnmzxcvbHJKLASDFGYUIOPQWERTNMZXCVB'
" 「'」 + 何かにマッピング
"http://haya14busa.com/vim-lazymotion-on-speed/
let g:EasyMotion_leader_key=";"
" 1 ストローク選択を優先する
let g:EasyMotion_grouping=1
" smartcase
let g:EasyMotion_smartcase = 1
let g:EasyMotion_use_migemo = 1
let g:EasyMotion_startofline=0

" anzu.vim
" mapping
nmap n nzz<Plug>(anzu-update-search-status)<Plug>(anzu-echo-search-status)
nmap N Nzz<Plug>(anzu-update-search-status)<Plug>(anzu-echo-search-status)
nmap * *zz<Plug>(anzu-update-search-status)<Plug>(anzu-echo-search-status)
nmap # #zz<Plug>(anzu-update-search-status)<Plug>(anzu-echo-search-status)
" clear status
nmap <Esc><Esc> :nohl<CR> <Plug>(anzu-clear-search-status)
" statusline
" set statusline=%{anzu#search_status()}
augroup vim-anzu
" 一定時間キー入力がないとき、ウインドウを移動したとき、タブを移動したときに
" 検索ヒット数の表示を消去する
    autocmd!
    autocmd CursorHold,CursorHoldI,WinLeave,TabLeave * call anzu#clear_search_status()
augroup END


" https://github.com/bkad/CamelCaseMotion
map <silent> w <Plug>CamelCaseMotion_w
map <silent> b <Plug>CamelCaseMotion_b
map <silent> e <Plug>CamelCaseMotion_e
omap <silent> iw <Plug>CamelCaseMotion_iw
xmap <silent> iw <Plug>CamelCaseMotion_iw
omap <silent> ib <Plug>CamelCaseMotion_ib
xmap <silent> ib <Plug>CamelCaseMotion_ib
omap <silent> ie <Plug>CamelCaseMotion_ie
xmap <silent> ie <Plug>CamelCaseMotion_ie
sunmap w
sunmap b
sunmap e

noremap <Leader>o :Occur<CR>

 " <Leader>mに、switch.vimをマッピング
 " nnoremap <Leader>m  <Plug>(switch-next)
 " nnoremap \ :Switch<cr>
let g:switch_mapping = '\'
" let g:switch_reverse_mapping = '|'

let g:switch_find_smallest_match = 0

 let g:switch_custom_definitions =
    \ [
    \   ['before', 'after'],
    \   ['int', 'float', 'double', 'string', 'null', 'undefined'],
    \   ['public', 'protected', 'private'],
    \   ['TRUE', 'FALSE'],
    \   ['front', 'back'],
    \   ['test', 'notest'],
    \   ['start', 'end'],
    \   ['import', 'export'],
    \   ['max', 'min'],
    \   ['increase', 'decrease'],
    \   ['get', 'set'],
    \   ['above', 'below'],
    \   ['jpg', 'png', 'gif'],
    \   ['new', 'old'],
    \   ['create', 'update', 'delete'],
    \   ['down', 'up'],
    \   ['left', 'right'],
    \   ['next', 'previous'],
    \   ['north', 'east', 'south', 'west'],
    \   ['yes', 'no'],
    \   ['ASC', 'DESC'],
    \   ['if', 'else', 'elseif'],
    \   ['==', '!=', '==='],
    \   ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    \ ]

" for pathogen
execute pathogen#infect()
filetype plugin indent on

" for NERDCommenter
" http://qiita.com/items/b69b41ad4ea2497b3477
let NERDSpaceDelims = 1
nmap ,, <Plug>NERDCommenterToggle
vmap ,, <Plug>NERDCommenterToggle

map <Leader>n :NERDTreeToggle<CR>
"NERDtreeで隠しファイルを表示する
let NERDTreeShowHidden=1

let NERDTreeMapChangeRoot='<right>'
let NERDTreeMapUpdir='<left>'
let NERDTreeMapOpenSplit='s'
let NERDTreeMapOpenVSplit='v'

if has("autocmd")
	" http://docs.racket-lang.org/guide/Vim.html
	autocmd vimrc BufNewFile,BufReadPost *.rkt,*.rktl set filetype=scheme

	autocmd vimrc BufNewFile,BufReadPost *.pegjs,*.language,*.grm  set filetype=pegjs
endif

call smartinput#define_rule({
\   'at': '\[\%#\]',
\   'char': '<CR>',
\   'input': '<CR><Esc>xO<C-g>u',
\ } )


call smartinput#define_rule({
\   'at': '{\%#}',
\   'char': '<CR>',
\   'input': '<Left><CR><Right><CR><Esc>O<C-g>u',
\   'filetype' : ['php'],
\ } )

" http://rhysd.hatenablog.com/entry/20121017/1350444269
" 改行時に行末スペースの除去
call smartinput#define_rule({
\   'at': '\s\+\%#',
\   'char': '<CR>',
\   'input': "<C-o>:call setline('.', substitute(getline('.'), '\\s\\+$', '', ''))<CR><CR><C-g>u",
\   })
" よく分からないけどundo区切りが他の方法で上手くいかないのでとりあえず暫定対応
call smartinput#define_rule({
\   'at': '\%#',
\   'char': '<CR>',
\   'input': "<CR><C-g>u",
\   })

" http://qiita.com/hara/items/1d30f6a6354fa480184b
" module, class, def, if, unless, case, while, until, for, begin に対応する end を補完
call smartinput#define_rule({
\ 'at': '^\%(.*=\)\?\s*\zs\%(module\|class\|def\|if\|unless\|case\|while\|until\|for\|begin\)\>\%(.*[^.:@$]\<end\>\)\@!.*\%#$',
\ 'char': '<CR>',
\ 'input': '<CR>end<Esc>O',
\ 'filetype': ['ruby'],
\ 'syntax': ['rubyBlock']
\ })

" do に対応する end を補完
call smartinput#define_rule({
\ 'at': '\<do\ze\%(\s*|.*|\)\=\s*\%#$',
\ 'char': '<CR>',
\ 'input': '<CR>end<Esc>O',
\ 'filetype': ['ruby'],
\ 'syntax': ['rubyDoBlock']
\ })

" ctrlp
" https://github.com/kien/ctrlp.vim
set runtimepath^=~/.vim/bundle/ctrlp.vim
let g:ctrlp_map = '<c-p>'
let g:ctrlp_cmd = 'CtrlPMixed'
let g:ctrlp_working_path_mode = 'ra'
set wildignore+=*/tmp/*,*.so,*.swp,*.zip     " MacOSX/Linux
set wildignore+=*/compiled/*     " MacOSX/Linux
" set wildignore+=*\\tmp\\*,*.swp,*.zip,*.exe  " Windows
let g:ctrlp_custom_ignore = '\v[\/]\.(git|hg|svn)$'
" The Silver Searcher
if executable('ag')
  " Use ag over grep
  set grepprg=ag\ --nogroup\ --nocolor
  let g:ag_prg="ag --smart-case --column --nogroup --noheading --nocolor"

  " Use ag in CtrlP for listing files. Lightning fast and respects .gitignore
  let g:ctrlp_user_command = 'ag %s -l --nocolor -g ""'
  let g:ag_highlight = 1 " highlight the search terms after searching

  " ag is fast enough that CtrlP doesn't need to cache
  " let g:ctrlp_use_caching = 0
else
  let g:ctrlp_user_command = 'find %s -type f'        " MacOSX/Linux
endif
" let g:ctrlp_user_command = 'ag %s'
" let g:ctrlp_use_migemo = 1
let g:ctrlp_clear_cache_on_exit = 0   " 終了時キャッシュをクリアしない
" let g:ctrlp_mruf_max            = 500 " MRUの最大記録数
let g:ctrlp_open_new_file       = 1   " 新規ファイル作成時にタブで開く
let g:ctrlp_available       = 1   " for yankround

" https://github.com/nixprime/cpsm
let g:ctrlp_match_func = {'match': 'cpsm#CtrlPMatch'}


" URLを開けるようにする
let g:netrw_nogx = 1 " disable netrw's gx mapping.
nmap gb <Plug>(openbrowser-smart-search)
vmap gb <Plug>(openbrowser-smart-search)

" http://blog.thomasupton.com/2012/05/syntastic/
" On by default, turn it off for html

" for jshint
let g:syntastic_mode_map = {
\ "mode" : "active",
\ "active_filetypes" : ["javascript", "json"],
\ 'passive_filetypes': ['scala']
\}

let g:syntastic_javascript_checkers = ['jshint']

let g:syntastic_loc_list_height=5

" http://stackoverflow.com/questions/17512794/toggle-error-location-panel-in-syntastic
function! ToggleErrors()
    if empty(filter(tabpagebuflist(), 'getbufvar(v:val, "&buftype") is# "quickfix"'))
         " No location/quickfix list shown, open syntastic error location panel
         Errors
    else
        lclose
    endif
endfunction

nnoremap <silent> <Leader>e :<C-u>call ToggleErrors()<CR>

" http://mba-hack.blogspot.jp/2013/03/unitevim.html
"" unite.vim {{{
" The prefix key.
nnoremap    [unite]   <Nop>
nmap    <Leader>u [unite]

let g:unite_source_history_yank_enable =1  "history/yankの有効化

" unite.vim keymap
" <a href="https://github.com/alwei/dotfiles/blob/3760650625663f3b08f24bc75762ec843ca7e112/.vimrc" target="_blank" rel="noreferrer" style="cursor:help;display:inline !important;">https://github.com/alwei/dotfiles/blob/3760650625663f3b08f24bc75762ec843ca7e112/.vimrc</a>
nnoremap [unite]u  :<C-u>Unite -no-split<Space>
nnoremap <silent> [unite]t :<C-u>Unite<Space>buffer -no-quit<CR>
" nnoremap <silent> [unite]b :<C-u>Unite<Space>bookmark<CR>
nnoremap <silent> [unite]b :<C-u>Unite<Space>vim_bookmarks<CR>
nnoremap <silent> [unite]c :<C-u>Unite<Space>colorscheme -auto-preview<CR>
nnoremap <silent> [unite]m :<C-u>Unite<Space>file_mru<CR>
nnoremap <silent> [unite]d :<C-u>UniteWithBufferDir file<CR>
nnoremap <silent> [unite]r :<C-u>Unite<Space>file_rec<CR>
nnoremap <silent> [unite]p :<C-u>Unite<Space>file_rec:!<CR>
nnoremap <silent> [unite]f :<C-u>UniteWithBufferDir -buffer-name=files file<CR>
nnoremap <silent> [unite]y :<C-u>Unite<Space>history/yank<CR>
nnoremap <silent> [unite]o :<C-u>Unite -vertical -winwidth=40<Space>outline<CR>
" http://d.hatena.ne.jp/osyo-manga/20130617/1371468776
nnoremap <silent> [unite]v :<C-u>Unite output:let<CR>
" nnoremap <silent> [unite]g :<C-u>Unite<Space>giti<CR>
" vimprocがいるらしい http://mba-hack.blogspot.jp/2013/03/unitevim.html
nnoremap <silent> [unite]g :<C-u>Unite grep:. -buffer-name=search-buffer -no-quit<CR>
nnoremap <silent> [unite]q :UniteResume<CR>
nnoremap <silent> [unite]/ :<C-u>Unite -buffer-name=search line -start-insert -no-quit<CR>
nnoremap <silent> [unite]h :<C-u>Unite -start-insert help<CR>
nnoremap <silent> [unite]l :<C-u>Unite line<CR>


" unite-build map
nnoremap <silent> ,vb :Unite build<CR>
nnoremap <silent> ,vcb :Unite build:!<CR>
nnoremap <silent> ,vch :UniteBuildClearHighlight<CR>
"" }}}

" カーソル位置の単語をgrep検索
nnoremap <silent> ,cg :<C-u>Unite grep:. -buffer-name=search-buffer<CR><C-R><C-W>

" unite grep に ag(The Silver Searcher) を使う
if executable('ag')
  let g:unite_source_grep_command = 'ag'
  let g:unite_source_grep_default_opts = '--nogroup --nocolor --column'
  let g:unite_source_grep_recursive_opt = ''
  let g:unite_source_rec_async_command =
        \ 'ag --follow --nocolor --nogroup --hidden -g ""'
  " ignore files
  call unite#custom#source('file_rec/async', 'ignore_pattern', '(png\|gif\|jpeg\|jpg)$')
endif

" Like ctrlp.vim settings.
  call unite#custom#profile('default', 'context', {
  \   'winheight': 10,
  \   'direction': 'botright',
  \ })

" https://github.com/Yggdroot/indentLine
let g:indentLine_color_term = 111
let g:indentLine_color_gui = '#708090'
let g:indentLine_char = '¦' "use ¦, ┆ or │

let s:my_action = { 'is_selectable' : 1 }
function! s:my_action.func(candidates)
  wincmd p
  exec 'tabe '. a:candidates[0].action__path
endfunction
call unite#custom_action('file', 'my_tabe', s:my_action)

let s:my_action = { 'is_selectable' : 1 }
function! s:my_action.func(candidates)
  wincmd p
  exec 'split '. a:candidates[0].action__path
endfunction
call unite#custom_action('file', 'my_split', s:my_action)

let s:my_action = { 'is_selectable' : 1 }
function! s:my_action.func(candidates)
  wincmd p
  exec 'vsplit '. a:candidates[0].action__path
endfunction
call unite#custom_action('file', 'my_vsplit', s:my_action)

" テキストオブジェクト
" 値に1が設定されていればマップを展開する

let g:expand_region_text_objects = {
\   'i"' : 1,
\   'a"' : 1,
\   'i)' : 1,
\   'a)' : 1,
\   'i}' : 1,
\   'a}' : 1,
\   'i]'  :1,
\   'a]'  :1,
\   'i''' :1,
\   'a''' :1,
\   'ip' : 1,
\   'is' : 1,
\   'iw'  :0,
\   'il'  :1,
\   'ie'  :1
\}

" Settings for neocomplete.
" Use neocomplete.
" let g:neocomplete#enable_at_startup = 1

" " 自動で補完しない
" let g:neocomplete#disable_auto_complete = 1

" " Use smartcase.
" let g:neocomplete#enable_smart_case = 1
" " Set minimum syntax keyword length.
" " https://twitter.com/dictav/status/287435117469761536
" let g:neocomplete#sources#syntax#min_keyword_length = 3
" let g:neocomplete#auto_completion_start_length = 3
" let g:neocomplete#lock_buffer_name_pattern = '\*ku\*'

" " 日本語入力中に補完されると日本語が打ち切れない（意味ない？）
" let g:neocomplete#lock_iminsert = 1


" " Define dictionary.
" let g:neocomplete#sources#dictionary#dictionaries = {
    " \ 'default' : '',
    " \ 'vimshell' : $HOME.'/.vimshell_hist',
    " \ 'scheme' : $HOME.'/.gosh_completions'
        " \ }

" " Define keyword.
" if !exists('g:neocomplete#keyword_patterns')
    " let g:neocomplete#keyword_patterns = {}
" endif

" "日本語を補完候補として取得しないようにする
" let g:neocomplete#keyword_patterns['default'] = '\h\w*'

" let g:neocomplete#cursor_hold_i_time = 1500

" " Plugin key-mappings.
" inoremap <expr><C-g>     neocomplete#undo_completion()
" inoremap <expr><C-Space>     neocomplete#start_manual_complete()

" " Recommended key-mappings.
" " <CR>: close popup and save indent.
" " imap <silent> <CR> <C-r>=<SID>my_cr_function()<CR>
" " imap <expr> <CR> pumvisible() ? neocomplete#close_popup() : "\<Plug>(smartinput_CR)"
      " " " \ neocomplete#close_popup() : "\<Plug>(smartinput_CR)"
" " function! s:my_cr_function()
  " " return pumvisible() ? neocomplete#close_popup() : "\<Plug>(smartinput_CR)"
" " endfunction
" " <C-h>, <BS>: close popup and delete backword char.
" " inoremap <expr><C-h> neocomplete#smart_close_popup()."\<C-h>"
" " inoremap <expr><BS> neocomplete#smart_close_popup()."\<C-h>"
" " plugin内で使われているので必須
" inoremap <expr><C-y>  neocomplete#close_popup()
" " inoremap <expr><C-e>  neocomplete#cancel_popup()
" " Close popup by <Space>.
" "inoremap <expr><Space> pumvisible() ? neocomplete#close_popup() : "\<Space>"

" " Or set this.
" let g:neocomplete#enable_cursor_hold_i = 1
" " Or set this.
" " let g:neocomplete#enable_insert_char_pre = 1

" " AutoComplPop like behavior.
" "let g:neocomplete#enable_auto_select = 1

" " Shell like behavior(not recommended).
" "set completeopt+=longest
" let g:neocomplete#enable_auto_select = 1
" "let g:neocomplete#disable_auto_complete = 1
" "inoremap <expr><TAB>  pumvisible() ? "\<Down>" : "\<C-x>\<C-u>"

" " Enable omni completion.
" autocmd vimrc FileType css setlocal omnifunc=csscomplete#CompleteCSS
" autocmd vimrc FileType html,markdown setlocal omnifunc=htmlcomplete#CompleteTags
" autocmd vimrc FileType javascript setlocal omnifunc=javascriptcomplete#CompleteJS
" autocmd vimrc FileType python setlocal omnifunc=pythoncomplete#Complete
" autocmd vimrc FileType xml setlocal omnifunc=xmlcomplete#CompleteTags

" " Enable heavy omni completion.
" if !exists('g:neocomplete#sources#omni#input_patterns')
  " let g:neocomplete#sources#omni#input_patterns = {}
" endif
" let g:neocomplete#sources#omni#input_patterns.php = '[^. \t]->\h\w*\|\h\w*::'
" let g:neocomplete#sources#omni#input_patterns.c = '[^.[:digit:] *\t]\%(\.\|->\)'
" let g:neocomplete#sources#omni#input_patterns.cpp = '[^.[:digit:] *\t]\%(\.\|->\)\|\h\w*::'

" " For perlomni.vim setting.
" " https://github.com/c9s/perlomni.vim
" let g:neocomplete#sources#omni#input_patterns.perl = '\h\w*->\h\w*\|\h\w*::'

" " Settings for neosnippet"
" " Plugin key-mappings.
" " imap <C-k>     <Plug>(neosnippet_expand_or_jump)
" smap <C-k>     <Plug>(neosnippet_expand_or_jump)
" xmap <C-k>     <Plug>(neosnippet_expand_target)

" " SuperTab like snippets behavior.
" imap <expr><TAB> neosnippet#expandable_or_jumpable() ?
" \ "\<Plug>(neosnippet_expand_or_jump)"
" \: pumvisible() ? "\<C-n>" : "\<TAB>"

" smap <expr><TAB> neosnippet#expandable_or_jumpable() ?
" \ "\<Plug>(neosnippet_expand_or_jump)"
" \: "\<TAB>"

" " For snippet_complete marker.
" if has('conceal')
  " set conceallevel=2 concealcursor=i
" endif
" " http://d.hatena.ne.jp/osyo-manga/20140820/1408546674
" autocmd InsertLeave * syntax clear neosnippetConcealExpandSnippets

" " Tell Neosnippet about the other snippets
" " let g:neosnippet#snippets_directory='~/.vim/bundle/vim-snippets/snippets'
" let g:neosnippet#snippets_directory='~/.vim/snippets'


let g:user_emmet_leader_key='<C-Z>'
" let g:user_emmet_leader_key='<c-x>'
let g:user_emmet_settings = {
\ 'variables': {
\ 'lang' : 'ja'
\ }
\}

" noremap <Leader>b :Autoformat<CR><CR>
" nnoremap <leader>b :%!js-beautify -j -q -B -f -<CR>
" autocmd vimrc FileType javascript nmap <silent> <buffer> <Leader>b :JsBeautifySimple<cr>
" autocmd vimrc FileType javascript vmap <silent> <buffer> <Leader>b :JsBeautifySimple<cr>
" autocmd vimrc FileType javascript let b:JsBeautifySimple_config = "~/.jsbeautifyrc"
map <Leader>b :call JsBeautify()<cr>
" or
autocmd FileType javascript noremap <buffer>  <Leader>b :call JsBeautify()<cr>
" for json
autocmd FileType json noremap <buffer> <Leader>b :call JsonBeautify()<cr>
" for jsx
autocmd FileType jsx noremap <buffer> <Leader>b :call JsxBeautify()<cr>
" for html
autocmd FileType html noremap <buffer> <Leader>b :call HtmlBeautify()<cr>
" for css or scss
autocmd FileType css noremap <buffer> <Leader>b :call CSSBeautify()<cr>
autocmd FileType javascript vnoremap <buffer>  <Leader>b :call RangeJsBeautify()<cr>
autocmd FileType json vnoremap <buffer> <Leader>b :call RangeJsonBeautify()<cr>
autocmd FileType jsx vnoremap <buffer> <Leader>b :call RangeJsxBeautify()<cr>
autocmd FileType html vnoremap <buffer> <Leader>b :call RangeHtmlBeautify()<cr>
autocmd FileType css vnoremap <buffer> <Leader>b :call RangeCSSBeautify()<cr>
command! JsBeautify :call JsBeautify()

" https://github.com/jelera/vim-javascript-syntax
" au FileType javascript call JavaScriptFold()

" http://layzie.hatenablog.com/entry/20130122/1358811539
" この設定入れるとshiftwidthを1にしてインデントしてくれる
let g:SimpleJsIndenter_BriefMode = 1
" この設定入れるとswitchのインデントがいくらかマシに
let g:SimpleJsIndenter_CaseIndentLevel = -1

let g:jsdoc_default_mapping = 0
" nnoremap <silent> <Leader>d :JsDoc<CR>

function! Gadd ()
  :Gwrite
  :echo 'git add [ ' . expand('%:t') . ' ].'
endfunction

nnoremap <silent> <Leader>gb :Gblame<CR>
nnoremap <silent> <Leader>gd :Gdiff<Space>
nnoremap <silent> <Leader>gs :Gstatus<CR>
" nnoremap <silent> <Leader>ga :Gwrite<CR> \| :echo 'git add [ ' . expand('%:t') . ' ].'<CR>
nnoremap <silent> <Leader>ga :call Gadd()<CR>
nnoremap <silent> <Leader>gc :Gcommit<CR>
nnoremap <silent> <Leader>gr :Gremove<CR>
nnoremap <silent> <Leader>gm :Gmove<CR>
nnoremap <silent> <Leader>gC :Gread<Space>
nnoremap <silent> <Leader>gl :Glog<CR>
nnoremap <silent> <Leader>gw :Gbrowse<CR>

" http://books.google.co.jp/books?id=QZSWbc83LfQC&pg=PA108&lpg=PA108&dq=vim+star&source=bl&ots=i5zfo7mhZO&sig=IRCOtnO0RclvQzyMVFLb5VG3ga4&hl=ja&sa=X&ei=cMsNVNvJCore8AWQ54H4BA&ved=0CH4Q6AEwCQ#v=onepage&q=vim%20star&f=false
" map * <Plug>(visualstar-*)N
" map # <Plug>(visualstar-#)N
map *   <Plug>(asterisk-*)
map #   <Plug>(asterisk-#)
map g*  <Plug>(asterisk-g*)
map g#  <Plug>(asterisk-g#)
map z*  <Plug>(asterisk-z*)
map gz* <Plug>(asterisk-gz*)
map z#  <Plug>(asterisk-z#)
map gz# <Plug>(asterisk-gz#)
nmap *   vis<Plug>(asterisk-*)
nmap #   vis<Plug>(asterisk-#)
nmap g*  vis<Plug>(asterisk-g*)
nmap g#  vis<Plug>(asterisk-g#)
nmap z*  vis<Plug>(asterisk-z*)
nmap gz* vis<Plug>(asterisk-gz*)
nmap z#  vis<Plug>(asterisk-z#)
nmap gz# vis<Plug>(asterisk-gz#)

nmap <Leader>h <Plug>(quickhl-manual-this)
xmap <Leader>h <Plug>(quickhl-manual-this)

nmap <Leader>H <Plug>(quickhl-manual-reset)
xmap <Leader>H <Plug>(quickhl-manual-reset)

" ハイライトするグループ名を設定します
" アンダーラインで表示する
" let g:brightest#highlight = {
" \   "group" : "BrightestUnderline"
" \}

" map /  <Plug>(incsearch-forward)
" (anzu-update-search-status)<Plug>(anzu-echo-search-status)
" map ?  <Plug>(incsearch-backward)
" どうもincsearchは日本語が打てないようなので最悪これで
" nnoremap <Leader>/ /
" nnoremap <Leader>? ?
" map g/ <Plug>(incsearch-stay)

"" for hl_matchit
let g:hl_matchit_enable_on_vim_startup = 1
let g:hl_matchit_hl_groupname = 'Title'
" let g:hl_matchit_allow_ft = 'html\|vim\|ruby\|sh\|smarty'
let g:hl_matchit_allow_ft = 'html\|vim\|ruby\|sh'

" http://d.hatena.ne.jp/oppara/20111229/p1
" phpStylist.php へのパス
let g:phpstylist_cmd_path = setting_files_path . '/bin/phpStylist.php'

" phpStylist のオプション
" php /path/to/phpStylist.php --help
 let g:phpstylist_options = {
    \ 'default' : [
      \ '--add_missing_braces ',
      \ '--align_array_assignment ',
      \ '--align_var_assignment ',
      \ '--indent_case ',
      \ '--indent_size 1 ',
      \ '--indent_with_tabs ',
      \ '--keep_redundant_lines ',
      \ '--line_before_comment_multi ',
      \ '--line_before_curly ',
      \ '--line_before_curly_function ',
      \ '--space_after_comma ',
      \ '--space_after_if ',
      \ '--space_around_arithmetic ',
      \ '--space_around_assignment ',
      \ '--space_around_colon_question ',
      \ '--space_around_comparison ',
      \ '--space_around_concat ',
      \ '--space_around_double_arrow ',
      \ '--space_around_logical ',
      \ '--space_inside_for ',
      \ '--vertical_array '
    \]
  \}

" Start interactive EasyAlign in visual mode (e.g. vip<Enter>)
vmap <Enter> <Plug>(EasyAlign)
" Start interactive EasyAlign for a motion/text object (e.g. gaip)
nmap ga <Plug>(EasyAlign)
let g:easy_align_ignore_groups = ['String']
" http://qiita.com/NanohaAsOnKai/items/5e196bfbb8c3d0b98385
let g:easy_align_delimiters = {
\    '=': {
\        'pattern': '===\|!==\|<=>\|\(&&\|||\|<<\|>>\)=\|=\~[#?]\?\|=>\|[:+/*!%^=><&|.-]\?=[#?]\?',
\        'left_margin': 1,
\        'right_margin': 1,
\        'stick_to_left': 0 },
\    '>': {
\        'pattern': '>>\|=>\|>'},
\    '/': {
\        'pattern':       '//\+\|/\*\|\*/',
\        'delimiter_align': 'l'},
\    '#': {
\        'pattern':         '#\+',
\        'delimiter_align': 'l', },
\    '$': {
\        'pattern':         '\((.*\)\@!$\(.*)\)\@!',
\        'right_margin':  0,
\        'delimiter_align': 'l', },
\    ']': {
\        'pattern':       '[[\]]',
\        'left_margin':   0,
\        'right_margin':  0,
\        'stick_to_left': 0, },
\    ')': {
\        'pattern':       '[()]',
\        'left_margin':   0,
\        'right_margin':  0,
\        'stick_to_left': 0, },
\    'd': {
\        'pattern':      ' \(\S\+\s*[;=]\)\@=',
\        'left_margin':  0,
\        'right_margin': 0, }, }

" for WordCount (percentage, line number, column number)
" https://github.com/fuenor/vim-wordcount
let g:airline_section_z = 'l:%l/%L|c:%c|wc:%{WordCount()}|%P'
set updatetime=1000

" (bufferline or filename)
" let g:airline_section_c = '%{getcwd()} | %t'
let g:airline_section_c = '%{getcwd()}'

nmap p <Plug>(yankround-p)
xmap p <Plug>(yankround-p)
" nmap P <Plug>(yankround-P)
nmap gp <Plug>(yankround-gp)
xmap gp <Plug>(yankround-gp)
nmap gP <Plug>(yankround-gP)
" M-p
nmap π <Plug>(yankround-prev)
 " M-n
nmap ˜ <Plug>(yankround-next)


" for Changed
" let g:Changed_definedSigns = 1
" sign define SIGN_CHANGED_DELETED_VIM text=- texthl=ChangedDeleteHl
" sign define SIGN_CHANGED_ADDED_VIM   text=+ texthl=ChangedAddHl
" sign define SIGN_CHANGED_VIM         text=* texthl=ChangedDefaultHl

" let g:easytags_events = ['BufWritePost']
" let g:easytags_async = 1

" http://qiita.com/tutu/items/fbc4023ebc3004964e86
" noremap <Leader>tv :vsp<CR> :exe("tjump ".expand('<cword>'))<CR>
" noremap <Leader>ts :split<CR> :exe("tjump ".expand('<cword>'))<CR>
" map <silent><Leader>tt <C-w><C-]><C-w>T
" nmap <Leader>tp vas<C-w>}
" noremap <Leader>tq <C-w><C-z>
" nmap <Leader>tn vas<C-]>
" noremap <Leader>tb <C-t>

" http://blog.supermomonga.com/articles/vim/share-cr-map-with-multiple-plugins.html
" if neobundle#tap('vim-smartinput')
  " function! neobundle#tapped.hooks.on_post_source(bundle)
    " " neosnippet and neocomplete compatible
    " call smartinput#map_to_trigger('i', '<Plug>(vimrc_cr)', '<Enter>', '<Enter>')
    " imap <expr><CR> !pumvisible() ? "\<Plug>(vimrc_cr)" :
          " \ neosnippet#expandable() ? "\<Plug>(neosnippet_expand)" :
          " \ neocomplete#close_popup()
  " endfunction
  " call neobundle#untap()
" endif

nnoremap <silent> <Leader>d :filetype detect<CR>

" nnoremap <F7> :VimShell -toggle -split<CR>
" inoremap <F7> <C-o>:VimShell -toggle -split<CR>
" nnoremap <Leader>qp :QuickRun php<CR>
" nnoremap <Leader>qr :QuickRun ruby<CR>

let g:gitgutter_map_keys = 0
let g:gitgutter_realtime = 0
let g:gitgutter_eager = 0

" カーソル移動で一覧と差分を更新させたくない
" let g:agit_enable_auto_show_commit = 0
" vimrc 設定例
" autocmd FileType agit call s:my_agit_setting()
" function! s:my_agit_setting()
  " nmap <buffer> ch <Plug>(agit-git-cherry-pick)
  " nmap <buffer> Rv <Plug>(agit-git-revert)
" endfunction

" http://qiita.com/c0hama/items/99a6f92323ca5e6fb730
" agit.vim を vimfiler や unite-file 内から開く
" let agit_file = { 'description' : 'open the file''s history in agit.vim' }
" function! agit_file.func(candidate)
    " execute 'AgitFile' '--file='.a:candidate.action__path
" endfunction
" call unite#custom#action('file', 'agit-file', agit_file)

call unite#custom#profile('source/vim_bookmarks', 'context', {
    \   'winheight': 13,
    \   'direction': 'botright',
    \   'start_insert': 0,
    \   'keep_focus': 1,
    \   'no_quit': 1,
    \ })

" https://github.com/StanAngeloff/php.vim
" let g:php_syntax_extensions_enabled = 1
function! PhpSyntaxOverride()
  hi! def link phpDocTags  phpDefine
  hi! def link phpDocParam phpType
  hi! def link phpDocIdentifier phpIdentifier
endfunction
augroup phpSyntaxOverride
  autocmd!
  autocmd FileType php call PhpSyntaxOverride()
augroup END

let g:lt_location_list_toggle_map = '<leader>l'
let g:lt_quickfix_list_toggle_map = '<leader>q'

" for SilverSearcher
let g:ag_highlight=1

" YouCompleteMe
let g:ycm_min_num_of_chars_for_completion = 5
let g:ycm_complete_in_comments = 1
let g:ycm_seed_identifiers_with_syntax = 1
let g:ycm_key_list_select_completion=[]
let g:ycm_key_list_previous_completion=[]

let g:UltiSnipsSnippetDirectories=[$HOME.'/.vim/ultisnips']

set completeopt-=preview
let g:ycm_add_preview_to_completeopt = 0
let g:ycm_auto_trigger = 1
let g:ycm_key_detailed_diagnostics = ''
let g:ycm_filetype_specific_completion_to_disable = {
      \ 'php': 1,
      \ 'smarty': 1
      \}

let g:csv_no_conceal = 1
" csv.vimをトグル
function! ToggleCsvPlugin()
  if exists('g:csv_no_conceal')
    unlet g:csv_no_conceal
  else
    let g:csv_no_conceal = 1
  endif
  :InitCSV
endfunction
command! ToggleCsvPlugin :call ToggleCsvPlugin()

" let g:ctrlsf_auto_close = 0
" let g:ctrlsf_default_root = 'project'

" winresier
let g:winresizer_gui_enable = 1
let g:winresizer_start_key = '<leader>w'
let g:winresizer_gui_start_key = '<leader>g'

" To indent 'case:' and 'default:' statements in switch() blocks: >
let g:PHP_vintage_case_default_indent = 1

nnoremap <silent> <Leader>fn :TagbarCurrentTag<CR>

nnoremap <Leader>fu :CtrlPFunky<Cr>
" narrow the list down with a word under cursor
nnoremap <Leader>fU :execute 'CtrlPFunky ' . expand('<cword>')<Cr>

" vimdiffで起動した際自動的に単語単位の差分(diffchar.vim)を有効にする
" http://qiita.com/takaakikasai/items/0d617b6e0aed490dff35
if &diff
  augroup enable_diffchar
    autocmd!
    autocmd VimEnter * execute "%SDChar"
  augroup END
endif

" f8はscratch-utilityで使われてるので回避
nmap <F6> <Plug>ToggleDiffCharCurrentLine
