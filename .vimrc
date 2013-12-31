"Vim Settings for CUI

" カラーリング
syntax on
set hlsearch " 検索結果文字列のハイライトを有効にする

set cursorline " カーソル行をハイライト
"set cursorcolumn
set background=dark

set title "編集中のファイル名を表示する
set showcmd "入力中のコマンドを表示する
set laststatus=2 "ステータスラインを常に表示する

"スワップファイルを生成しない
" set noswapfile
"バックアップファイルを生成しない
" set nobackup

" http://nanasi.jp/articles/howto/file/seemingly-unneeded-file.html
set swapfile
set directory=~/.backup/vim/swap

set backup
set backupdir=~/.backup/vim/backup

" 行番号の表示
set number
" カーソルが何行目の何列目に置かれているかを表示する
set ruler
set title "編集中のファイル名を表示する

" http://d.hatena.ne.jp/ruicc/20090615/1245086039
set nocompatible               " be iMproved



" オートインデントを有効にする（新しい行のインデントを現在の行と同じにする）
set autoindent
"C言語スタイルのインデント機能が有効
set cindent
" タブが対応する空白の数
set tabstop=2
" タブやバックスペースの使用等の編集操作をするときに、タブが対応する空白の数
set softtabstop=2
" インデントの各段階に使われる空白の数
set shiftwidth=2
" 新しい行を作ったときに高度な自動インデントを行う
set smartindent

" 閉じ括弧が入力されたとき、対応する括弧を表示する
set showmatch

" カーソルを行頭、行末で止まらないようにする
set whichwrap=b,s,h,l,<,>,[,]

" コマンドライン補完を拡張モードにする
set wildmenu

" 検索の時に大文字小文字を区別しない
set ignorecase
" 最後まで検索したら先頭に戻る
set wrapscan
" インクリメンタルサーチ(検索文字を打ち込むと即検索)
set incsearch
set smartcase " 検索文字列に大文字が含まれている場合は区別して検索する

set autoread " ファイル内容が変更されると自動読み込みする

" タブ文字を自動削除しない（効かない・・・）
" http://vim-users.jp/2010/04/hack137/
" nnoremap o oX<C-h>
" nnoremap O OX<C-h>
" inoremap <CR> <CR>X<C-h>

set copyindent
set preserveindent


" タブラインを常に表示
set showtabline=2


" http://shoken.hatenablog.com/entry/20120617/p
set splitbelow "新しいウィンドウを下に開く
set splitright "新しいウィンドウを右に開く

" folding
" http://www.ksknet.net/vi/post_183.html
" set foldmethod=syntax
" set foldmethod=indent
set foldmethod=manual
set foldlevel=100 "Don't autofold anything


" http://win-to-mac.blogspot.jp/2012/08/vim.html
set statusline=%<%f\ %m%r%h%w%{'['.(&fenc!=''?&fenc:&enc).']['.&ff.']'}%=%l,%c%V%8P

" for WordCOunt
" https://github.com/fuenor/vim-wordcount/blob/master/wordcount.vim
set statusline+=[wc:%{WordCount()}]
set updatetime=500

" http://blog.remora.cx/2011/08/display-invisible-characters-on-vim.html
set list
set listchars=tab:»-,trail:-,extends:»,precedes:«,nbsp:%
"set listchars=tab:»-,trail:-,eol:↲,extends:»,precedes:«,nbsp:%

"_でも単語区切り
" https://sites.google.com/site/vimdocja/usr_05-html
set iskeyword-=_

" 全角スペース・行末のスペース・タブの可視化
if has("syntax")
    syntax on

    " PODバグ対策
    syn sync fromstart

    function! ActivateInvisibleIndicator()
        " 下の行の"　"は全角スペース
        syntax match InvisibleJISX0208Space "　" display containedin=ALL
        highlight InvisibleJISX0208Space term=underline ctermbg=Blue guibg=darkgray gui=underline
        "syntax match InvisibleTrailedSpace "[ \t]\+$" display containedin=ALL
        "highlight InvisibleTrailedSpace term=underline ctermbg=Red guibg=NONE gui=undercurl guisp=darkorange
        "syntax match InvisibleTab "\t" display containedin=ALL
        "highlight InvisibleTab term=underline ctermbg=white gui=undercurl guisp=darkslategray
    endfunction

    augroup invisible
        autocmd! invisible
        autocmd BufNew,BufRead * call ActivateInvisibleIndicator()
    augroup END
endif

" http://qiita.com/katton/items/bc9720826120f5f61fc1
function! s:remove_dust()
    let cursor = getpos(".")
    " 保存時に行末の空白を除去する
    %s/\s\+$//ge
	" 保存時に行末のタブ文字を除去する
    %s/\t\+$//ge

    " 保存時にtabを2スペースに変換する
    "%s/\t/  /ge
    call setpos(".", cursor)
    unlet cursor
endfunction
autocmd BufWritePre * call <SID>remove_dust()

" http://vim-users.jp/2009/09/hack69/
set autochdir
" command! -nargs=? -complete=dir -bang CD  call s:ChangeCurrentDir('<args>', '<bang>')
" function! s:ChangeCurrentDir(directory, bang)
    " if a:directory == ''
        " lcd %:p:h
    " else
        " execute 'lcd' . a:directory
    " endif

    " if a:bang == ''
        " pwd
    " endif
" endfunction

" " Change current directory.
" nnoremap <silent> <Space>cd :<C-u>CD<CR>

" http://d.hatena.ne.jp/spiritloose/20061113/1163401194
inoremap { {}<LEFT>
inoremap [ []<LEFT>
inoremap ( ()<LEFT>
inoremap " ""<LEFT>
inoremap ' ''<LEFT>
vnoremap { "zdi{<C-R>z}<ESC>
vnoremap [ "zdi[<C-R>z]<ESC>
vnoremap ( "zdi(<C-R>z)<ESC>
vnoremap " "zdi"<C-R>z"<ESC>
vnoremap ' "zdi'<C-R>z'<ESC>

" http://d.hatena.ne.jp/thata/20100606/1275796513
"カーソルを表示行で移動する。物理行移動は<C-n>,<C-p>
nnoremap j gj
nnoremap k gk
nnoremap <Down> gj
nnoremap <Up>   gk

" http://vim-users.jp/2009/08/hack57/
nnoremap O :<C-u>call append(expand('.'), '')<Cr>j
nnoremap <C-Tab> gt
nnoremap <C-S-Tab> gT
" nnoremap <C-S-Tab> gT

" Gはファイルの終端に移動
nnoremap G G<End>
vnoremap G G<End>
onoremap G G<End>
" ちょっと微妙かもだけど、9で行末に移動
nnoremap 9 <End>
vnoremap 9 <End>
onoremap 9 <End>

" 1つ前の検索ワードを表示
nnoremap g/ /<C-P>
" {}括弧をfoldする
nnoremap z/ zf%

" super keyでWindow移動（MacVimのみ）
" http://qiita.com/ukitazume/items/e5df95feab1c2412cb3a
nnoremap <C-j> <C-w>j
nnoremap <C-k> <C-w>k
nnoremap <C-h> <C-w>h
nnoremap <C-l> <C-w>l
nnoremap <C-M-Left> <C-w><Left>
nnoremap <C-M-Up> <C-w><Up>
nnoremap <C-M-Down> <C-w><Down>
nnoremap <C-M-Right> <C-w><Right>

nnoremap <C-Left> gT
nnoremap <C-Right> gt

" http://stackoverflow.com/questions/2005214/switching-to-a-particular-tab-in-vim
" Jump to particular tab directly
"NORMAL mode bindings for gvim
noremap <unique> <D-1> 1gt
noremap <unique> <D-2> 2gt
noremap <unique> <D-3> 3gt
noremap <unique> <D-4> 4gt
noremap <unique> <D-5> 5gt
noremap <unique> <D-6> 6gt
noremap <unique> <D-7> 7gt
noremap <unique> <D-8> 8gt
noremap <unique> <D-9> 9gt
noremap <unique> <D-0> 10gt
"INSERT mode bindings for gvim
inoremap <unique> <D-1> <C-O>1gt
inoremap <unique> <D-2> <C-O>2gt
inoremap <unique> <D-3> <C-O>3gt
inoremap <unique> <D-4> <C-O>4gt
inoremap <unique> <D-5> <C-O>5gt
inoremap <unique> <D-6> <C-O>6gt
inoremap <unique> <D-7> <C-O>7gt
inoremap <unique> <D-8> <C-O>8gt
inoremap <unique> <D-9> <C-O>9gt
inoremap <unique> <D-0> <C-O>10gt



" 他のアプリケーションとのコピー&ペースト
" https://sites.google.com/site/hymd3a/vim/vim-copy-paste
" :set clipboard=unnamed
"*x  切り取り
vnoremap gx "+x
"*y  コピー
vnoremap gy "+y
"*p  ペースト
nnoremap gp "+p


" ESCを2回入力で検索時のハイライトを解除
" nnoremap <Esc><Esc> :nohlsearch<CR>

" オムニ補完
" http://d.hatena.ne.jp/arerreee/20120726/1343316762
imap <C-Space> <C-x><C-o>

" インサートモードで改行
" http://cohalz.com/2013/06/14/vim-easier-enter-keymap/
inoremap <C-j> <ESC>$a<CR>
nnoremap <C-j> $a<CR>

" http://notachi.hatenadiary.jp/entry/2012/11/13/181810
" カーソル移動
" inoremap <C-p> <Up>
" inoremap <C-n> <Down>
" inoremap <C-b> <Left>
" inoremap <C-f> <Right>
inoremap <C-e> <End>
inoremap <C-a> <Home>
inoremap <C-d> <Del>
" カーソルのある行を画面中央に
inoremap <C-l> <C-o>zz
" カーソルより前の文字を削除
inoremap <C-u> <C-o>d0
" カーソルより後の文字を削除
inoremap <C-k> <c-o>D
" アンドゥ
inoremap <C-x>u <C-o>u
inoremap <C-]> <C-o>u
" 貼りつけ
inoremap <C-y> <C-o>P

" vimrcをリロード
" http://whileimautomaton.net/2008/07/20150335
" nnoremap <Space>s  :<C-u>source $VIMRC<Return>
nnoremap <Space>s  :<C-u>source ~/.vimrc <Return>


" anzu.vim
" mapping
nmap n <Plug>(anzu-n-with-echo)
nmap N <Plug>(anzu-N-with-echo)
nmap * <Plug>(anzu-star-with-echo)
nmap # <Plug>(anzu-sharp-with-echo)

" clear status
nmap <Esc><Esc> :nohl<CR> <Plug>(anzu-clear-search-status)

" https://github.com/bkad/CamelCaseMotion
map <silent> w <Plug>CamelCaseMotion_w
map <silent> b <Plug>CamelCaseMotion_b
map <silent> e <Plug>CamelCaseMotion_e
sunmap w
sunmap b
sunmap e
" statusline
" set statusline=%{anzu#search_status()}
" http://www.daisaru11.jp/blog/2011/08/vim%E3%81%A7%E6%8C%BF%E5%85%A5%E3%83%A2%E3%83%BC%E3%83%89%E3%81%AB%E3%81%AA%E3%82%89%E3%81%9A%E3%81%AB%E6%94%B9%E8%A1%8C%E3%82%92%E5%85%A5%E3%82%8C%E3%82%8B/
" noremap <CR> o<ESC>

" http://d.hatena.ne.jp/tyru/20130430/vim_resident
"call singleton#enable()

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
" カラー設定変更
"hi EasyMotionTarget ctermbg=none ctermfg=red
"hi EasyMotionShade  ctermbg=none ctermfg=blue

" for Vundle
" https://github.com/gmarik/vundle
 filetype off                   " required!

 set rtp+=~/.vim/bundle/vundle/
 call vundle#rc()

 " let Vundle manage Vundle
 " required!
 Bundle 'gmarik/vundle'

 " My Bundles here:
 Bundle 'derekwyatt/vim-scala'
 Bundle 'yonchu/accelerated-smooth-scroll'
 Bundle 'haya14busa/vim-easymotion'
 " Bundle 'kana/vim-smartinput'
 " Bundle 'mhinz/vim-startify'
 " Bundle 'osyo-manga/vim-over'
 Bundle 'AndrewRadev/switch.vim'
 Bundle 'terryma/vim-multiple-cursors'
 Bundle 'tyru/open-browser.vim'
" <Space>mに、switch.vimをマッピング
" nnoremap <Space>m  <Plug>(switch-next)
nnoremap ^ :Switch<cr>

" for pathogen
execute pathogen#infect()
filetype plugin indent on

" for NERDCommenter
" http://qiita.com/items/b69b41ad4ea2497b3477
let NERDSpaceDelims = 1
nmap ,, <Plug>NERDCommenterToggle
vmap ,, <Plug>NERDCommenterToggle

map <Esc>f :NERDTreeToggle<CR>
"NERDtreeで隠しファイルを表示する
let NERDTreeShowHidden=1

if has("autocmd")
	" http://docs.racket-lang.org/guide/Vim.html
	autocmd BufNewFile,BufReadPost *.rkt,*.rktl set filetype=scheme

	autocmd BufNewFile,BufReadPost *.pegjs,*.language,*.grm  set filetype=pegjs
endif

" call smartinput#map_to_trigger('i', '<Plug>(smartinput_BS)','<BS>','<BS>')
" call smartinput#map_to_trigger('i', '<Plug>(smartinput_C-h)', '<BS>', '<C-h>')
" call smartinput#map_to_trigger('i', '<Plug>(smartinput_CR)','<Enter>','<Enter>')


" neocomplcache
" https://github.com/Shougo/neocomplcache.vim
"Note: This option must set it in .vimrc(_vimrc).  NOT IN .gvimrc(_gvimrc)!
" Use neocomplcache.
let g:neocomplcache_enable_at_startup = 1
" Use smartcase.
let g:neocomplcache_enable_smart_case = 1
" Set minimum syntax keyword length.
let g:neocomplcache_min_syntax_length = 3
let g:neocomplcache_lock_buffer_name_pattern = '\*ku\*'

" Enable heavy features.
" Use camel case completion.
"let g:neocomplcache_enable_camel_case_completion = 1
" Use underbar completion.
let g:neocomplcache_enable_underbar_completion = 1
" let g:NeoComplCache_SkipInputTime = '1.5'
"方向キーによる自動展開を防止
"https://github.com/Shougo/neocomplcache.vim/issues/369
"日本語が途中で補完されて上手く打ち込めない
" let g:neocomplcache_enable_insert_char_pre = 1
" let g:neocomplcache_enable_cursor_hold_i = 1
" For cursor moving in insert mode(Not recommended)
" inoremap <expr><Left>  neocomplcache#close_popup() . "\<Left>"
" inoremap <expr><Right> neocomplcache#close_popup() . "\<Right>"
" inoremap <expr><Up>    neocomplcache#close_popup() . "\<Up>"
" inoremap <expr><Down>  neocomplcache#close_popup() . "\<Down>"

" Shell like behavior(not recommended).
set completeopt+=longest
let g:neocomplcache_enable_auto_select = 1
let g:neocomplcache_disable_auto_complete = 1
inoremap <expr><TAB>  pumvisible() ? "\<Down>" : "\<C-x>\<C-u>"

" Define dictionary.
let g:neocomplcache_dictionary_filetype_lists = {
    \ 'default' : '',
    \ 'vimshell' : $HOME.'/.vimshell_hist',
    \ 'scheme' : $HOME.'/.gosh_completions'
        \ }
inoremap <expr><Up> pumvisible() ? neocomplcache#close_popup()."\<Up>" : "\<Up>"
inoremap <expr><Down> pumvisible() ? neocomplcache#close_popup()."\<Down>" : "\<Down>"
" Define keyword.
if !exists('g:neocomplcache_keyword_patterns')
    let g:neocomplcache_keyword_patterns = {}
endif
let g:neocomplcache_keyword_patterns['default'] = '\h\w*'
" Plugin key-mappings.
inoremap <expr><C-g>     neocomplcache#undo_completion()
inoremap <expr><C-l>     neocomplcache#complete_common_string()
" Recommended key-mappings.
" <CR>: close popup and save indent.
" imap <silent> <CR> <C-r>=<SID>my_cr_function()<CR>
inoremap <silent> <CR> <C-r>=<SID>my_cr_function()<CR>
" inoremap <expr> <CR> neocomplcache#close_popup() . eval(smartinput#sid().'_trigger_or_fallback("\<Enter>", "\<Enter>")')
function! s:my_cr_function()
	return pumvisible() ? neocomplcache#close_popup() : "\<CR>"
	" return pumvisible() ? neocomplcache#close_popup() : "\<Plug>(smartinput_CR)"
endfunction

" <TAB>: completion.
inoremap <expr><TAB>  pumvisible() ? "\<C-n>" : "\<TAB>"
" <C-h>, <BS>: close popup and delete backword char.
inoremap <expr><C-h> neocomplcache#smart_close_popup()."\<C-h>"
inoremap <expr><BS> neocomplcache#smart_close_popup()."\<C-h>"
" inoremap <expr> <BS> neocomplcache#smart_close_popup() . eval(smartinput#sid().'_trigger_or_fallback("\<BS>", "\<BS>")')
inoremap <expr><C-y>  neocomplcache#close_popup()
inoremap <expr><C-e>  neocomplcache#cancel_popup()
" Enable omni completion.
autocmd FileType css setlocal omnifunc=csscomplete#CompleteCSS
autocmd FileType html,markdown setlocal omnifunc=htmlcomplete#CompleteTags
autocmd FileType javascript setlocal omnifunc=javascriptcomplete#CompleteJS
autocmd FileType python setlocal omnifunc=pythoncomplete#Complete
autocmd FileType xml setlocal omnifunc=xmlcomplete#CompleteTags
" Enable heavy omni completion.
if !exists('g:neocomplcache_omni_patterns')
  let g:neocomplcache_omni_patterns = {}
endif
let g:neocomplcache_omni_patterns.php = '[^. \t]->\h\w*\|\h\w*::'
let g:neocomplcache_omni_patterns.c = '[^.[:digit:] *\t]\%(\.\|->\)'
let g:neocomplcache_omni_patterns.cpp = '[^.[:digit:] *\t]\%(\.\|->\)\|\h\w*::'

" ctrlp
" https://github.com/kien/ctrlp.vim
set runtimepath^=~/.vim/bundle/ctrlp.vim
let g:ctrlp_map = '<c-p>'
let g:ctrlp_cmd = 'CtrlP'
let g:ctrlp_working_path_mode = 'c' " the directory of the current file.
set wildignore+=*/tmp/*,*.so,*.swp,*.zip     " MacOSX/Linux
set wildignore+=*\\tmp\\*,*.swp,*.zip,*.exe  " Windows
let g:ctrlp_custom_ignore = '\v[\/]\.(git|hg|svn)$'
" let g:ctrlp_user_command = 'find %s -type f'        " MacOSX/Linux

" http://vim-users.jp/2011/08/hack225/
let g:netrw_nogx = 1 " disable netrw's gx mapping.
nmap gx <Plug>(openbrowser-smart-search)
vmap gx <Plug>(openbrowser-smart-search)

" http://blog.thomasupton.com/2012/05/syntastic/
" On by default, turn it off for html
let g:syntastic_mode_map = { 'mode': 'active',
	\ 'active_filetypes': [],
	\ 'passive_filetypes': ['scala'] }
