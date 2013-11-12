"Vim Settings for CUI

" カラーリング
syntax on
set hlsearch " 検索結果文字列のハイライトを有効にする

set cursorline " カーソル行をハイライト
"set cursorcolumn
set background=dark

set laststatus=2 "ステータスラインを常に表示する

set title "編集中のファイル名を表示する
set showcmd "入力中のコマンドを表示する
set laststatus=2 "ステータスラインを常に表示する

"スワップファイルを生成しない
set noswapfile
"バックアップファイルを生成しない
set nobackup

" 行番号の表示
set number
" カーソルが何行目の何列目に置かれているかを表示する
set ruler
set title "編集中のファイル名を表示する

" http://d.hatena.ne.jp/ruicc/20090615/1245086039
set nocompatible               " be iMproved

" http://d.hatena.ne.jp/thata/20100606/1275796513
"カーソルを表示行で移動する。物理行移動は<C-n>,<C-p>
nnoremap j gj
nnoremap k gk
nnoremap <Down> gj
nnoremap <Up>   gk

" オートインデントを有効にする（新しい行のインデントを現在の行と同じにする）
set autoindent
"C言語スタイルのインデント機能が有効
set cindent
" タブが対応する空白の数
set tabstop=4
" タブやバックスペースの使用等の編集操作をするときに、タブが対応する空白の数
set softtabstop=4
" インデントの各段階に使われる空白の数
set shiftwidth=4
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

" タブ文字を自動削除しない
" http://vim-users.jp/2010/04/hack137/
nnoremap o oX<C-h>
nnoremap O OX<C-h>
inoremap <CR> <CR>X<C-h>

" http://vim-users.jp/2009/08/hack57/
nnoremap O :<C-u>call append(expand('.'), '')<Cr>j

" タブラインを常に表示
set showtabline=2

nnoremap <C-Tab> gt
nnoremap <C-S-Tab> gT

" Gはファイルの終端に移動
nnoremap G G<End>
" ちょっと微妙かもだけど、9で行末に移動
nnoremap 9 <End>


" http://shoken.hatenablog.com/entry/20120617/p
set splitbelow "新しいウィンドウを下に開く
set splitright "新しいウィンドウを右に開く

" folding
" http://www.ksknet.net/vi/post_183.html
set foldmethod=syntax
set foldlevel=100 "Don't autofold anything

" http://d.hatena.ne.jp/pinoyuki/20120425/p1
" nnoremap gy "0P

" 他のアプリケーションとのコピー&ペースト
" https://sites.google.com/site/hymd3a/vim/vim-copy-paste
" :set clipboard=unnamed
"*x  切り取り
vnoremap gx "+x
"*y  コピー
vnoremap gy "+y
"*p  ペースト
nnoremap gp "+p

" :map <C-U> <C-Y><C-Y><C-Y><C-Y><C-Y><C-Y><C-Y><C-Y><C-Y><C-Y><C-Y><C-Y><C-Y><C-Y><C-Y><C-Y>
" :map <C-D> <C-E><C-E><C-E><C-E><C-E><C-E><C-E><C-E><C-E><C-E><C-E><C-E><C-E><C-E><C-E><C-E>

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

" http://www.daisaru11.jp/blog/2011/08/vim%E3%81%A7%E6%8C%BF%E5%85%A5%E3%83%A2%E3%83%BC%E3%83%89%E3%81%AB%E3%81%AA%E3%82%89%E3%81%9A%E3%81%AB%E6%94%B9%E8%A1%8C%E3%82%92%E5%85%A5%E3%82%8C%E3%82%8B/
noremap <CR> o<ESC>

" http://d.hatena.ne.jp/tyru/20130430/vim_resident
"call singleton#enable()

" ホームポジションに近いキーを使う
" http://blog.remora.cx/2012/08/vim-easymotion.html
"let g:EasyMotion_keys='hjklasdfgyuiopqwertnmzxcvbHJKLASDFGYUIOPQWERTNMZXCVB'
" 「'」 + 何かにマッピング
let g:EasyMotion_leader_key=";"
" 1 ストローク選択を優先する
let g:EasyMotion_grouping=1
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

autocmd BufNewFile,BufReadPost *.pegjs set filetype=pegjs
autocmd BufNewFile,BufReadPost *.language set filetype=pegjs
autocmd BufNewFile,BufReadPost *.grm set filetype=pegjs

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
"let g:neocomplcache_enable_underbar_completion = 1

" Define dictionary.
let g:neocomplcache_dictionary_filetype_lists = {
    \ 'default' : '',
    \ 'vimshell' : $HOME.'/.vimshell_hist',
    \ 'scheme' : $HOME.'/.gosh_completions'
        \ }

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
inoremap <silent> <CR> <C-r>=<SID>my_cr_function()<CR>
function! s:my_cr_function()
  return pumvisible() ? neocomplcache#close_popup() : "\<CR>"
endfunction
" <TAB>: completion.
inoremap <expr><TAB>  pumvisible() ? "\<C-n>" : "\<TAB>"
" <C-h>, <BS>: close popup and delete backword char.
inoremap <expr><C-h> neocomplcache#smart_close_popup()."\<C-h>"
inoremap <expr><BS> neocomplcache#smart_close_popup()."\<C-h>"
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


