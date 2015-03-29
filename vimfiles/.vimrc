"Vim Settings for CUI

" カラーリング
syntax on
set hlsearch " 検索結果文字列のハイライトを有効にする

set encoding=utf-8
scriptencoding utf-8

" ミュートにする。
set t_vb=
set visualbell
set noerrorbells

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

" http://stackoverflow.com/questions/15660669/what-is-a-un-file-or-or-why-does-vim-in-the-terminal-make-the-un-file
if has('persistent_undo')
  set undofile
  set undodir=~/.backup/vim/undo
endif

" http://nanasi.jp/articles/howto/file/seemingly-unneeded-file.html
set swapfile
set directory=~/.backup/vim/swap

set backup
set backupdir=~/.backup/vim/backup

" 行番号の表示
set number
" カーソルが何行目の何列目に置かれているかを表示する
set ruler

" http://d.hatena.ne.jp/ruicc/20090615/1245086039
if &compatible
  set nocompatible
endif

" http://vim-users.jp/2010/04/hack137/
" オートインデントを有効にする（新しい行のインデントを現在の行と同じにする）
set autoindent
" set copyindent
" set preserveindent
"C言語スタイルのインデント機能が有効
set cindent
" タブに展開
set expandtab
" タブが対応する空白の数
set tabstop=2
" タブやバックスペースの使用等の編集操作をするときに、タブが対応する空白の数
set softtabstop=2
" インデントの各段階に使われる空白の数
set shiftwidth=2
" 新しい行を作ったときに高度な自動インデントを行う
" set smartindent
"行頭の余白内で Tab を打ち込むと、'shiftwidth' の数だけインデントする
set smarttab

" 自動改行しない
" http://kaworu.jpn.org/kaworu/2007-07-29-1.php
set textwidth=0

" 閉じ括弧が入力されたとき、対応する括弧を表示する
set showmatch

" % で移動する括弧の構成に <> を追加する
set matchpairs+=<:>

" カーソルを行頭、行末で止まらないようにする
set whichwrap=b,s,h,l,<,>,[,]

" コマンドライン補完を拡張モードにする
set wildmenu

" コマンドモードでの補完設定
" set wildmode=longest:full,list
set wildmode=list:full,longest:full

" 検索の時に大文字小文字を区別しない
set ignorecase
" 最後まで検索したら先頭に戻る
set wrapscan
" インクリメンタルサーチ(検索文字を打ち込むと即検索)
set incsearch
set smartcase " 検索文字列に大文字が含まれている場合は区別して検索する
set gdefault "置換の時 g オプションをデフォルトで有効にする

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

" set paste
" http://vim.wikia.com/wiki/Toggle_auto-indenting_for_code_paste
nnoremap <F6> :set invpaste paste?<CR>
imap <F6> <C-O>:set invpaste paste?<CR>
set pastetoggle=<F6>
set showmode

" folding
" http://www.ksknet.net/vi/post_183.html
" set foldmethod=syntax
" set foldmethod=indent
set foldmethod=manual
set foldlevel=100 "Don't autofold anything

" http://blog.remora.cx/2011/08/display-invisible-characters-on-vim.html
set list
set listchars=tab:»-,trail:-,extends:»,precedes:«,nbsp:%
"set listchars=tab:»-,trail:-,eol:↲,extends:»,precedes:«,nbsp:%

"_でも単語区切り
" https://sites.google.com/site/vimdocja/usr_05-html
set iskeyword-=_

" http://qiita.com/takeh1k0/items/b66b8a66bb4073084ee5
set ambiwidth=double

" http://superuser.com/questions/22444/make-vim-display-a-line-at-the-edge-of-the-set-textwidth
set colorcolumn=80
" highlight ColorColumn ctermbg=green guibg=orange
" highlight ColorColumn cterm=italic gui=none

" http://vim.wikia.com/wiki/Make_search_results_appear_in_the_middle_of_the_screen
" set scrolloff=999
set scrolloff=5

" 権限無いファイルでも保存
cabbrev w!! w !sudo tee % >/dev/null


" http://rbtnn.hateblo.jp/entry/2014/11/30/174749
augroup vimrc
  autocmd!
augroup END

" http://tech-tec.com/archives/934
let g:mapleader=" "


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

" http://stackoverflow.com/questions/6496778/vim-run-autocmd-on-all-filetypes-except
let remove_dust_blacklist = ['php', 'smarty']
autocmd vimrc BufWritePre * if index(remove_dust_blacklist, &ft) < 0 | call <SID>remove_dust()
" autocmd BufWritePre * call <SID>remove_dust()


" http://vim-users.jp/2009/09/hack69/
" set autochdir

" http://superuser.com/questions/195022/vim-how-to-synchronize-nerdtree-with-current-opened-tab-file-path
autocmd BufEnter * lcd %:p:h
" http://qiita.com/shiena/items/1e98fd14d0ef0084b17f
" nnoremap <Leader>c :lcd %:h<cr>
cabbrev cdc :lcd %:h

vnoremap <Leader>{ "zdi{<C-R>z}<ESC>
vnoremap [ "zdi[<C-R>z]<ESC>
vnoremap ( "zdi(<C-R>z)<ESC>
vnoremap " "zdi"<C-R>z"<ESC>
vnoremap ' "zdi'<C-R>z'<ESC>
" vnoremap < S> " インデントと衝突><

" http://d.hatena.ne.jp/thata/20100606/1275796513
"カーソルを表示行で移動する。物理行移動は<C-n>,<C-p>
nnoremap j gj
nnoremap k gk
nnoremap gj j
nnoremap gk k
nnoremap <Down> gj
nnoremap <Up>   gk

" Alt-f, Alt-bを無理矢理マッピング
" http://stackoverflow.com/questions/7501092/can-i-map-alt-key-in-vim
" inoremap ƒ <ESC>lwi

" M-f
" noremap! ƒ <C-o>w
noremap! ƒ <S-Right>
" M-b
noremap! ∫ <S-Left>
" M-j
noremap! Ô <C-o>O
" M-d
noremap! ∂ <C-o>dw

" http://vim-users.jp/2009/08/hack57/
nnoremap <Enter> :<C-u>call append(expand('.'), '')<Cr>j
nnoremap <C-Tab> gt
nnoremap <C-S-Tab> gT
nnoremap gr gT
" nnoremap <C-S-Tab> gT

" Gはファイルの終端に移動
nnoremap G G<End>
vnoremap G G<End>
onoremap G G<End>

" ちょっと微妙かもだけど、\で行末に移動
nnoremap \ <End>
vnoremap \ <End>
onoremap \ <End>

" ヴィジュアルモードでdeleteで削除
" MacのdeleteはBackSpaceらしい
" vnoremap <DEL> d
vnoremap <BS> d

" 1つ前の検索ワードを表示
" nnoremap // /<C-P>
" {}括弧をfoldする
nnoremap z/ zf%

" super keyでWindow移動（MacVimのみ）
" http://qiita.com/ukitazume/items/e5df95feab1c2412cb3a
" nnoremap <C-j> <C-w>j
" nnoremap <C-k> <C-w>k
" nnoremap <C-h> <C-w>h
" nnoremap <C-l> <C-w>l

nnoremap <C-M-Left> <C-w><Left>
nnoremap <C-M-Up> <C-w><Up>
nnoremap <C-M-Down> <C-w><Down>
nnoremap <C-M-Right> <C-w><Right>

" 挿入モードでもタブ移動したい！
nnoremap <C-Left> gT
nnoremap <C-Right> gt

" Ctrlでjkhlをパワーアップ
nnoremap <C-j> 5j
nnoremap <C-k> 5k
nnoremap <C-h> 5h
nnoremap <C-l> 5l

" http://stackoverflow.com/questions/2005214/switching-to-a-particular-tab-in-vim
" Jump to particular tab directly
"NORMAL mode bindings for gvim
noremap <D-1> 1gt
noremap <D-2> 2gt
noremap <D-3> 3gt
noremap <D-4> 4gt
noremap <D-5> 5gt
noremap <D-6> 6gt
noremap <D-7> 7gt
noremap <D-8> 8gt
noremap <D-9> 9gt
noremap <D-0> 10gt
"INSERT mode bindings for gvim
inoremap <D-1> <C-O>1gt
inoremap <D-2> <C-O>2gt
inoremap <D-3> <C-O>3gt
inoremap <D-4> <C-O>4gt
inoremap <D-5> <C-O>5gt
inoremap <D-6> <C-O>6gt
inoremap <D-7> <C-O>7gt
inoremap <D-8> <C-O>8gt
inoremap <D-9> <C-O>9gt
inoremap <D-0> <C-O>10gt

" 他のアプリケーションとのコピー&ペースト
" https://sites.google.com/site/hymd3a/vim/vim-copy-paste
" :set clipboard=unnamed
"*x  切り取り
vnoremap <Leader>x "+x
"*y  コピー
vnoremap <Leader>y "+y
"*p  ペースト
nnoremap <Leader>p "+p

" http://vim.wikia.com/wiki/Format_pasted_text_automatically
" :nnoremap p ]p
" :nnoremap ]p p


" http://cohama.hateblo.jp/entry/2013/10/07/020453
nnoremap <F4> :<C-u>setlocal relativenumber!<CR>
inoremap <F4> <C-O>:setlocal relativenumber!<CR>

" nnoremap <M-j> j
inoremap <C-Left> <Esc>gT
inoremap <C-Right> <Esc>gt

" ESCを2回入力で検索時のハイライトを解除
" nnoremap <Esc><Esc> :nohlsearch<CR>

" オムニ補完
" http://d.hatena.ne.jp/arerreee/20120726/1343316762
" imap <C-Space> <C-x><C-o>

" インサートモードで改行
" http://cohalz.com/2013/06/14/vim-easier-enter-keymap/
inoremap <C-j> <ESC>$a<CR>
" nnoremap <C-j> $a<CR>

" inoremap , ,<Space>


" http://easyramble.com/disable-vim-auto-comment.html
"
" set formatoptions-=ro
" autocmd vimrc FileType * setlocal formatoptions-=ro
" autocmd FileType * setlocal formatoptions-=ro
autocmd FileType * setlocal formatoptions-=c formatoptions-=r formatoptions-=o

" visulaモードで選択してからのインデント調整で調整後に選択範囲を開放しない
vnoremap > >gv
vnoremap < <gv

" http://notachi.hatenadiary.jp/entry/2012/11/13/181810
" カーソル移動
noremap! <C-p> <Up>
noremap! <C-n> <Down>
noremap! <C-b> <Left>
noremap! <C-f> <Right>
noremap! <C-e> <End>
noremap! <C-a> <Home>
noremap! <C-d> <Del>

" http://cohama.hateblo.jp/entry/20130529/1369843236
" cnoremap <expr> / (getcmdtype() == '/') '\/' : '/'
" cnoremap <C-o> <C-\>e(getcmdtype() == '/' <Bar><Bar> getcmdtype() == '?') ? '\<' . getcmdline() . '\>' : getcmdline()<CR>

" http://linuxserver.jp/%E3%82%BD%E3%83%95%E3%83%88%E3%82%A6%E3%82%A7%E3%82%A2/%E3%83%86%E3%82%AD%E3%82%B9%E3%83%88%E3%82%A8%E3%83%87%E3%82%A3%E3%82%BF/vim/%E3%82%B3%E3%83%9E%E3%83%B3%E3%83%89%E3%83%A2%E3%83%BC%E3%83%89%E3%81%A7%E3%81%AE%E3%83%9A%E3%83%BC%E3%82%B9%E3%83%88.php
noremap! <C-v> <C-r>"


" inoremap <M-Left> <Left>
" inoremap <M-b> <M-left>
" カーソルのある行を画面中央に
inoremap <C-l> <C-o>zz
" カーソルより前の文字を削除
" inoremap <C-u> <C-o>d0
" カーソルより後の文字を削除
inoremap <C-k> <c-o>D
" inoremap <C-.> <c-o>dd
" アンドゥ
" inoremap <C-x>u <C-o>u
noremap! <C-u> <C-o>u
noremap! <C-]> <C-o>u
noremap! <C-r> <C-o><C-r>
" 貼りつけ
" noremap! <C-y> <C-o>P
noremap! ∆ <C-o>O

" inoremap <C-i> <C-o>=

" vimrcをリロード
" http://whileimautomaton.net/2008/07/20150335
" nnoremap <Space>s  :<C-u>source $VIMRC<Return>
nnoremap <Leader>s  :<C-u>source ~/.vimrc <Return> :<C-u>source ~/.gvimrc <Return>
command! ReloadVimrc  :source ~/.vimrc

" http://tech.toshiya240.com/articles/2014/06/matchit-vim/
:source $VIMRUNTIME/macros/matchit.vim
augroup matchit
  au!
  au FileType ruby let b:match_words = '\<\(module\|class\|def\|begin\|do\|if\|unless\|case\)\>:\<\(elsif\|when\|rescue\)\>:\<\(else\|ensure\)\>:\<end\>'
augroup END

"コピーしながら括弧移動
" nnoremap <C-%> y%%

" 検索をバッファローカルに
" http://d.hatena.ne.jp/tyru/20140129/localize_search_options
" Localize search options.
" autocmd WinLeave *
" \     let b:vimrc_pattern = @/
" \   | let b:vimrc_hlsearch = &hlsearch
" autocmd WinEnter *
" \     let @/ = get(b:, 'vimrc_pattern', @/)
" \   | let &l:hlsearch = get(b:, 'vimrc_hlsearch', &l:hlsearch)


" http://www.daisaru11.jp/blog/2011/08/vim%E3%81%A7%E6%8C%BF%E5%85%A5%E3%83%A2%E3%83%BC%E3%83%89%E3%81%AB%E3%81%AA%E3%82%89%E3%81%9A%E3%81%AB%E6%94%B9%E8%A1%8C%E3%82%92%E5%85%A5%E3%82%8C%E3%82%8B/
" noremap <CR> o<ESC>

" http://d.hatena.ne.jp/tyru/20130430/vim_resident
"call singleton#enable()

" for grep
" http://qiita.com/yuku_t/items/0c1aff03949cb1b8fe6b
autocmd vimrc QuickFixCmdPost *grep* cwindow
set grepprg=grep\ -nH


" http://qiita.com/Linda_pp/items/ee4bf64b1fe2c0a32cbd
" 行頭 → 非空白行頭をローテートする
" function! s:rotate_in_line()
    " let c = col('.')

    " let cmd = c == 1 ? '^' : '0'
    " execute "normal! ".cmd
" endfunction
" 行頭 → 非空白行頭 → 行末 をローテートする
function! s:rotate_in_line()
    let c = col('.')

    let cmd = c == 1 ? '^' : '$'
    execute "normal! ".cmd

    if c == col('.')
        if cmd == '^'
            normal! $
        else
            normal! 0
        endif
    endif
endfunction
" 0 に割り当て
nnoremap <silent>0 :<C-u>call <SID>rotate_in_line()<CR>

" undoを区切る
" http://haya14busa.com/vim-break-undo-sequence-in-insertmode/
inoremap <Space> <Space><C-g>u
" inoremap <CR> <CR><C-g>u

" </で閉じタグを自動補完
" http://qiita.com/hail2u/items/26c473677b2ce5672876
autocmd FileType html inoremap <silent> <buffer> </ </<C-x><C-o>

" 編集位置の自動復帰
" http://blog.papix.net/entry/2012/12/14/042937
" au BufReadPost * if line("'\"") > 1 && line("'\"") <= line("$") | exe "normal! g`\""

" 括弧補完。カーソルを自動的に()の中へ
" imap { {}<Left>
" imap [ []<Left>
" imap ( ()<Left>
" imap " ""<Left>
" imap ' ''<Left>

" smartinputによって顔文字が入力できないことがあるので、回避策
nnoremap <F5> :<C-u>setlocal imdisable!<CR>
inoremap <F5> <C-O>:setlocal imdisable!<CR>


" インデントレベルが同じ行を探して移動する
" http://qiita.com/crispy/items/ff3522a327d0a7d7706b
func! s:IndentSensitive(backward)
  let lineNum = line('.')
  let line = getline(lineNum)
  let col = col('.')
  call cursor(lineNum, 1)
  let indentLevel = s:getIndentLevel(line)
  let nextLine = getline(lineNum + (a:backward ? -1 : 1))
  let nextIndentLevel = s:getIndentLevel(nextLine)
  let pattern = printf('^[ \t]\{%d}[^ \t]', indentLevel)
  if indentLevel != nextIndentLevel
    let hitLineNum = search(pattern, 'n' . (a:backward ? 'b' : ''))
  else
    let lastLineNum = line('$')
    let hitLineNum = lineNum
    while 1 <= lineNum && lineNum <= lastLineNum
      let lineNum += a:backward ? -1 : 1
      if lineNum < 1
        break
      endif
      if s:getIndentLevel(getline(lineNum)) != indentLevel
        break
      end
      let hitLineNum = lineNum
    endwhile
  endif
  call cursor(hitLineNum, col)
endfunc
func! s:getIndentLevel(str)
  return len(matchstr(a:str, '^[ \t]*'))
endfunc
func! IndentSensitivePrev()
  call s:IndentSensitive(1)
endfunc
func! IndentSensitiveNext()
  call s:IndentSensitive(0)
endfunc
nnoremap <silent> <Leader>k :call IndentSensitivePrev()<CR>
nnoremap <silent> <Leader>j :call IndentSensitiveNext()<CR>


" 各タブページのカレントバッファ名+αを表示
function! s:tabpage_label(n)
  " t:title と言う変数があったらそれを使う
  let title = gettabvar(a:n, 'title')
  if title !=# ''
    return title
  endif

  " タブページ内のバッファのリスト
  let bufnrs = tabpagebuflist(a:n)

  " カレントタブページかどうかでハイライトを切り替える
  let hi = a:n is tabpagenr() ? '%#TabLineSel#' : '%#TabLine#'

  " バッファが複数あったらバッファ数を表示
  let no = len(bufnrs)
  if no is 1
    let no = ''
  endif
  " タブページ内に変更ありのバッファがあったら '+' を付ける
  let mod = len(filter(copy(bufnrs), 'getbufvar(v:val, "&modified")')) ? '+' : ''
  let sp = (no . mod) ==# '' ? '' : ' '  " 隙間空ける

  " カレントバッファ
  let curbufnr = bufnrs[tabpagewinnr(a:n) - 1]  " tabpagewinnr() は 1 origin
  let fname = pathshorten(bufname(curbufnr))

  let label = no . mod . sp . fname

  return '%' . a:n . 'T' . hi . label . '%T%#TabLineFill#'
endfunction
" http://d.hatena.ne.jp/thinca/20111204/1322932585
function! MakeTabLine()
  let titles = map(range(1, tabpagenr('$')), 's:tabpage_label(v:val)')
  let sep = ' | '  " タブ間の区切り
  let tabpages = join(titles, sep) . sep . '%#TabLineFill#%T'
  let info = ''  " 好きな情報を入れる
  let info .= fnamemodify(getcwd(), ":~") . ' '
  " current function info (cfi.vim)
  " let info .= cfi#format('%s()' . sep, '')
  return tabpages . '%=' . info  " タブリストを左に、情報を右に表示
endfunction

set tabline=%!MakeTabLine()

function! AlignBenchmark() abort
  let s:list = []
  global/^SCRIPT/
        \ call add(s:list, printf("%s\t%s",
        \                         matchstr(getline(line('.')+2), '\d\+\.\d\+'),
        \                         matchstr(getline('.'), 'SCRIPT\s*\zs.*$')))
  new
  put =reverse(sort(s:list))
  1 delete _
endfunction

" Plugins

 if has('vim_starting')
   if &compatible
     set nocompatible               " Be iMproved
   endif

   " Required:
   set runtimepath+=~/.vim/bundle/neobundle.vim/
 endif

 " Required:
 call neobundle#begin(expand('~/.vim/bundle/'))

 " Let NeoBundle manage NeoBundle
 " Required:
 NeoBundleFetch 'Shougo/neobundle.vim'


 " My Bundles here:
 " Refer to |:NeoBundle-examples|.
 " Note: You don't set neobundle setting in .gvimrc!


 " NeoBundle 'yonchu/accelerated-smooth-scroll'
 NeoBundle 'haya14busa/vim-easymotion'
 NeoBundle 'kana/vim-smartinput'
 " NeoBundle 'mhinz/vim-startify'
 " NeoBundle 'osyo-manga/vim-over'
 " NeoBundle 'terryma/vim-multiple-cursors'
 " NeoBundle 'haya14busa/vim-migemo'
 NeoBundle 'Yggdroot/indentLine'
 " NeoBundle 'Shougo/vimfiler.vim'
 NeoBundle 'terryma/vim-expand-region'
 NeoBundle 'Shougo/neocomplete.vim'
 NeoBundle 'Shougo/neosnippet'
 NeoBundle 'Shougo/neosnippet-snippets'
 NeoBundle 'kien/ctrlp.vim'
 NeoBundle 'scrooloose/nerdcommenter'
 NeoBundle 'scrooloose/syntastic'
 " NeoBundle 'Valloric/YouCompleteMe'
 " NeoBundle 'SirVer/ultisnips'
 " NeoBundle 'honza/vim-snippets'
 " NeoBundle 'maksimr/vim-jsbeautify'
 " NeoBundle 'einars/js-beautify'
 " NeoBundle 'Chiel92/vim-autocsformat'
 NeoBundle 'tpope/vim-surround'
 " NeoBundle 'pangloss/vim-javascript'
 NeoBundle 'kana/vim-textobj-line'
 NeoBundle 'kana/vim-textobj-entire'
 NeoBundle 'kana/vim-textobj-user'
 " NeoBundle 'euoia/vim-jsbeautify-simple'
 " NeoBundle 'alpaca-tc/beautify.vim'
 " NeoBundle 'Lokaltog/vim-powerline'
 NeoBundle 'tpope/vim-fugitive'
 NeoBundle 'Shougo/neomru.vim'
 " NeoBundle 'thinca/vim-visualstar'
 NeoBundle 't9md/vim-quickhl'
 NeoBundle 'osyo-manga/vim-brightest'
 NeoBundle 'haya14busa/incsearch.vim'
 NeoBundle 'rhysd/clever-f.vim'
 NeoBundle 'vimtaku/hl_matchit.vim'
 " NeoBundle 'kana/vim-smartword'
 NeoBundle 'bling/vim-airline'
 " NeoBundle 'jiangmiao/auto-pairs'
 " NeoBundle 'cohama/vim-smartinput-endwise'
 NeoBundle 'lilydjwg/colorizer'
 NeoBundle 'tyru/open-browser-github.vim'
 NeoBundle 'tpope/vim-abolish'
 NeoBundle 'LeafCage/yankround.vim'
 NeoBundle 'vim-scripts/Changed'
 " NeoBundle 'tacahiroy/ctrlp-funky'
 " NeoBundle 'h1mesuke/unite-outline'
 NeoBundle 'Shougo/unite-outline'
 " NeoBundle 'soramugi/auto-ctags.vim'
 NeoBundle 'xolox/vim-misc'
 NeoBundle 'xolox/vim-easytags'
 NeoBundle 'kana/vim-textobj-jabraces'
 NeoBundle 'thinca/vim-textobj-comment'
 NeoBundle 'saihoooooooo/vim-textobj-space'
 NeoBundle 'ujihisa/unite-colorscheme'
 NeoBundle 'haya14busa/vim-asterisk'
 " NeoBundle 'mtth/scratch.vim'
 NeoBundle 'violetyk/scratch-utility'
 " NeoBundle 'deris/vim-loadafterft'
 NeoBundle 'vim-scripts/SearchComplete'
 NeoBundle 'blueyed/vim-diminactive'
 " NeoBundle 'airblade/vim-gitgutter'
 NeoBundle 'sgur/vim-lazygutter'


 NeoBundle 'Shougo/vimproc.vim', {
       \ 'build' : {
       \     'windows' : 'tools\\update-dll-mingw',
       \     'cygwin' : 'make -f make_cygwin.mak',
       \     'mac' : 'make -f make_mac.mak',
       \     'linux' : 'make',
       \     'unix' : 'gmake',
       \    },
       \ }

NeoBundleLazy "majutsushi/tagbar", {
      \ "autoload": { "commands": ["TagbarToggle"] }}
if ! empty(neobundle#get("tagbar"))
   " Width (default 40)
  " let g:tagbar_width = 20
  " Map for toggle
  nn <silent> <leader>tt :TagbarToggle<CR>
endif

NeoBundleLazy 'Shougo/unite.vim' , {
\   'autoload' : { 'commands' : [ 'Unite' ] }
\ }
let s:bundle = neobundle#get('unite.vim')
function! s:bundle.hooks.on_source(bundle)
  " unite.vimの設定
  " ウィンドウを水平分割なら下に、垂直分割なら右に開く
  let g:unite_split_rule = 'botright'
  " vinarise
  " let g:vinarise_enable_auto_detect = 1
  " ESCキーを2回押すと終了する
  au FileType unite nnoremap <silent> <buffer> <ESC><ESC> :q<CR>
  au FileType unite inoremap <silent> <buffer> <ESC><ESC> <ESC>:q<CR>

  "インサートモードで開始
  " let g:unite_enable_start_insert = 1
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
	  "ctrl+bでブックマーク
	  nnoremap <silent> <buffer> <expr> b unite#do_action('bookmark')
	  inoremap <silent> <buffer> <expr> <C-b> unite#do_action('bookmark')
  endfunction"}}}

endfunction

" lazy load
NeoBundleLazy 'mattn/emmet-vim',{
                          \"autoload" : {"filetypes" :["html", "smarty"]}
                          \}
NeoBundleLazy 'derekwyatt/vim-scala',{
                          \"autoload" : {"filetypes" :["scala"]}
                          \}
NeoBundleLazy 'jelera/vim-javascript-syntax',{
                          \"autoload" : {"filetypes" :["javascript"]}
                          \}
NeoBundleLazy 'heavenshell/vim-jsdoc',{
                          \"autoload" : {"filetypes" :["javascript"]}
                          \}
NeoBundleLazy 'rhysd/vim-textobj-ruby',{
                          \"autoload" : {"filetypes" :["ruby"]}
                          \}
NeoBundleLazy 'oppara/phpstylist.vim',{
                          \"autoload" : {"filetypes" :["php"]}
                          \}
NeoBundleLazy 'mkiken/vim-jsbeautify-simple',{
                          \"autoload" : {"filetypes" :["javascript"]}
                          \}
NeoBundleLazy  'AndrewRadev/switch.vim',{
\   'autoload' : { 'commands' : [ "Switch"] }
                          \}
NeoBundleLazy 'tyru/open-browser.vim',{
\   'autoload' : { 'commands' : [ "OpenBrowserSmartSearch"] }
                          \}
NeoBundleLazy 'thinca/vim-qfreplace',{
\   'autoload' : { 'commands' : [ "Qfreplace"] }
                          \}
NeoBundleLazy  'rking/ag.vim',{
\   'autoload' : { 'commands' : [ "Ag", "AgFile"] }
                          \}
NeoBundleLazy 'deris/vim-diffbuf',{
\   'autoload' : { 'commands' : [ "DiffBuf"] }
                          \}
NeoBundleLazy 'junegunn/vim-easy-align',{
\   'autoload' : { 'commands' : [ "EasyAlign"] }
                          \}
NeoBundleLazy 'gregsexton/gitv',{
\   'autoload' : { 'commands' : [ "Gitv", "Gitv!"] }
                          \}
NeoBundleLazy 'scrooloose/nerdtree',{
\   'autoload' : { 'commands' : [ 'NERDTreeToggle'] }
                          \}
NeoBundleLazy 'Shougo/vimshell.vim',{
\   'autoload' : { 'commands' : [ 'VimShell', 'VimShellPop'] }
                          \}
NeoBundleLazy 'thinca/vim-quickrun',{
\   'autoload' : { 'commands' : [ 'QuickRun'] }
                          \}
 call neobundle#end()

 " Required:
 filetype plugin indent on

 " If there are uninstalled bundles found on startup,
 " this will conveniently prompt you to install them.
 NeoBundleCheck


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
" map f <Plug>(easymotion-fl)
" map f ;f
" map t ;t
" map F ;F
" map T ;T
" nmap s <Plug>(easymotion-s)


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
 nnoremap ^ :Switch<cr>
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
    \   ['up', 'down'],
    \   ['create', 'update', 'delete']
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

" 改行系のmappingにはundo区切りのために<C-g>uつける
" call smartinput#map_to_trigger('i', '<Plug>(smartinput_BS)','<BS>','<BS>')
" call smartinput#map_to_trigger('i', '<Plug>(smartinput_C-h)', '<BS>', '<C-h>')
" call smartinput#map_to_trigger('i', '<Plug>(smartinput_CR)','<Enter>','<Enter>')

call smartinput#define_rule({
\   'at': '\[\%#\]',
\   'char': '<CR>',
\   'input': '<CR><Esc>O<C-g>u',
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
" Ruby で文字列内展開 #{} やブロック引数 do || の補助
" call smartinput#map_to_trigger('i', '#', '#', '#')
" call smartinput#define_rule({
            " \   'at'       : '\%#',
            " \   'char'     : '#',
            " \   'input'    : '#{}<Left>',
            " \   'filetype' : ['ruby'],
            " \   'syntax'   : ['Constant', 'Special'],
            " \   })

" call smartinput#map_to_trigger('i', '<Bar>', '<Bar>', '<Bar>')
" call smartinput#define_rule({
            " \   'at' : '\({\|\<do\>\)\s*\%#',
            " \   'char' : '<Bar>',
            " \   'input' : '<Bar><Bar><Left>',
            " \   'filetype' : ['ruby'],
            " \    })

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

  " Use ag in CtrlP for listing files. Lightning fast and respects .gitignore
  let g:ctrlp_user_command = 'ag %s -l --nocolor -g ""'

  " ag is fast enough that CtrlP doesn't need to cache
  " let g:ctrlp_use_caching = 0
else
  let g:ctrlp_user_command = 'find %s -type f'        " MacOSX/Linux
endif
" let g:ctrlp_user_command = 'ag %s'
" let g:ctrlp_use_migemo = 1
" let g:ctrlp_clear_cache_on_exit = 0   " 終了時キャッシュをクリアしない
" let g:ctrlp_mruf_max            = 500 " MRUの最大記録数
let g:ctrlp_open_new_file       = 1   " 新規ファイル作成時にタブで開く
let g:ctrlp_available       = 1   " for yankround


" URLを開けるようにする
" http://vim-users.jp/2011/08/hack225/
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
" function! ToggleErrors()
"     let old_last_winnr = winnr('$')
"     lclose
"     if old_last_winnr == winnr('$')
"         " Nothing was closed, open syntastic error location panel
"         Errors
"     endif
" endfunction

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
nmap    <Leader>f [unite]

" unite.vim keymap
" <a href="https://github.com/alwei/dotfiles/blob/3760650625663f3b08f24bc75762ec843ca7e112/.vimrc" target="_blank" rel="noreferrer" style="cursor:help;display:inline !important;">https://github.com/alwei/dotfiles/blob/3760650625663f3b08f24bc75762ec843ca7e112/.vimrc</a>
nnoremap [unite]u  :<C-u>Unite -no-split<Space>
nnoremap <silent> [unite]t :<C-u>Unite<Space>buffer<CR>
nnoremap <silent> [unite]b :<C-u>Unite<Space>bookmark<CR>
nnoremap <silent> [unite]c :<C-u>Unite<Space>colorscheme -auto-preview<CR>
nnoremap <silent> [unite]m :<C-u>Unite<Space>file_mru<CR>
nnoremap <silent> [unite]d :<C-u>UniteWithBufferDir file<CR>
nnoremap <silent> [unite]r :<C-u>Unite<Space>file_rec<CR>
nnoremap <silent> [unite]p :<C-u>Unite<Space>file_rec:!<CR>
nnoremap <silent> [unite]f :<C-u>UniteWithBufferDir -buffer-name=files file<CR>
nnoremap <silent> [unite]y :<C-u>Unite<Space>yankaround<CR>
nnoremap <silent> [unite]o :<C-u>Unite -vertical -winwidth=40<Space>outline<CR>
" vimprocがいるらしい http://mba-hack.blogspot.jp/2013/03/unitevim.html
" nnoremap <silent> [unite]g :<C-u>Unite grep:. -buffer-name=search-buffer<CR>
nnoremap <silent> ,vr :UniteResume<CR>


" unite-build map
nnoremap <silent> ,vb :Unite build<CR>
nnoremap <silent> ,vcb :Unite build:!<CR>
nnoremap <silent> ,vch :UniteBuildClearHighlight<CR>
"" }}}



" http://qiita.com/kentaro/items/10b6dd5e3e1104dc6acc
" nnoremap <silent> <Leader>p  :Unite file_rec:!<CR>

" http://d.hatena.ne.jp/h1mesuke/20110918/p1
" nnoremap <silent> [unite]p :<C-u>call <SID>unite_project('-start-insert')<CR>
" function! s:unite_project(...)
"   let opts = (a:0 ? join(a:000, ' ') : '')
"   let dir = unite#util#path2project_directory(expand('%'))
"   execute 'Unite' opts 'file_rec:' . dir
" endfunction

" if executable('ag')
"     " Use ag in unite grep source.
"     let g:unite_source_grep_command = 'ag'
"     let g:unite_source_grep_recursive_opt = 'HRn'
"     let g:unite_source_grep_default_opts =
"     \ '--line-numbers --nocolor --nogroup --hidden --ignore ' .
"     \  '''.hg'' --ignore ''.svn'' --ignore ''.git'' --ignore ''.bzr'''
" endif

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



" let g:indent_guides_enable_on_vim_startup = 1
" let g:indent_guides_auto_colors = 0
" " set list lcs=tab:┊\
" " indent guides
" augroup indentguides
" 	autocmd!
" 	autocmd VimEnter,Colorscheme * :hi IndentGuidesOdd  guibg=blue   ctermbg=3
" 	autocmd VimEnter,Colorscheme * :hi IndentGuidesEven guibg=yellow ctermbg=4
" 	let g:indent_guides_start_level = 2
" 	let g:indent_guides_guide_size = 1
" augroup END

" https://github.com/Yggdroot/indentLine
let g:indentLine_color_term = 111
let g:indentLine_color_gui = '#708090'
let g:indentLine_char = '¦' "use ¦, ┆ or │

" https://github.com/Shougo/vimfiler.vim
" vimfiler behaves as default explorer like netrw.
" let g:vimfiler_as_default_explorer = 1
" nnoremap <Esc>f :VimFilerExplorer<Cr>
" nnoremap <Esc>f :VimFiler<Cr>

" http://hrsh7th.hatenablog.com/entry/20120229/1330525683
" nnoremap <Leader>e :VimFiler -buffer-name=explorer -split -winwidth=25 -toggle -no-quit<Cr>


" let g:netrw_liststyle=0
" nnoremap <Leader>e :VimFilerExplorer -buffer-name=explorer -split -winwidth=45 -toggle -no-quit<Cr>
" autocmd! FileType vimfiler call g:My_vimfiler_settings()
" function! g:My_vimfiler_settings()
"   nmap     <buffer><expr><Cr> vimfiler#smart_cursor_map("\<Plug>(vimfiler_expand_tree)", "\<Plug>(vimfiler_edit_file)")
"   nnoremap <buffer>t          :call vimfiler#mappings#do_action('my_tabe')<Cr>
"   nnoremap <buffer>s          :call vimfiler#mappings#do_action('my_split')<Cr>
"   nnoremap <buffer>v          :call vimfiler#mappings#do_action('my_vsplit')<Cr>
"   nmap     <buffer><expr><Left> vimfiler#smart_cursor_map("\<Plug>(vimfiler_smart_h)", "\<Plug>(vimfiler_smart_h)")
"   nmap     <buffer><expr><Right> vimfiler#smart_cursor_map("\<Plug>(vimfiler_smart_l)", "\<Plug>(vimfiler_smart_l)")

  " nnoremap <buffer><Left> h :call vimfiler#mappings#vimfiler_smart_h

" endfunction

" autocmd FileType vimfiler nmap <Left> <buffer> <Plug>(vimfiler_smart_h)

" let g:vimfiler_default_columns = 'type'
" let g:vimfiler_explorer_columns = 'type'


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



" https://github.com/terryma/vim-expand-region

map + <Plug>(expand_region_expand)
map - <Plug>(expand_region_shrink)

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

" https://github.com/SirVer/ultisnips

" " Trigger configuration. Do not use <tab> if you use https://github.com/Valloric/YouCompleteMe.
" " let g:UltiSnipsExpandTrigger="<cr>"
" " let g:UltiSnipsExpandTrigger="<>"
" " let g:UltiSnipsJumpForwardTrigger="<c-b>"
" " let g:UltiSnipsJumpBackwardTrigger="<c-z>"

" " If you want :UltiSnipsEdit to split your window.
" let g:UltiSnipsEditSplit="vertical"


" " https://github.com/Valloric/YouCompleteMe/issues/36#issuecomment-15451411
" let g:UltiSnipsExpandTrigger       = "<tab>"
" let g:UltiSnipsJumpForwardTrigger  = "<tab>"
" let g:UltiSnipsJumpBackwardTrigger = "<s-tab>"
" let g:UltiSnipsSnippetDirectories  = ["snips"]

" function! g:UltiSnips_Complete()
"     call UltiSnips#ExpandSnippet()
"     if g:ulti_expand_res == 0
"         if pumvisible()
"             return "\<C-n>"
"         else
"             call UltiSnips#JumpForwards()
"             if g:ulti_jump_forwards_res == 0
"                return "\<TAB>"
"             endif
"         endif
"     endif
"     return ""
" endfunction

" au InsertEnter * exec "inoremap <silent> " . g:UltiSnipsExpandTrigger . " <C-R>=g:UltiSnips_Complete()<cr>"


" " Settings for YouCompleteMe
" " https://github.com/Valloric/YouCompleteMe
" let g:ycm_complete_in_comments = 1    " コメント内でも補完
" let g:ycm_seed_identifiers_with_syntax = 1    "ファイルに合ったシンタックスで補完
" " let g:ycm_cache_omnifunc = 0
" " let g:ycm_key_select_completion = "<CR>"


" Settings for neocomplete.
" Use neocomplete.
let g:neocomplete#enable_at_startup = 1

" 自動で補完しない
let g:neocomplete#disable_auto_complete = 1

" Use smartcase.
let g:neocomplete#enable_smart_case = 1
" Set minimum syntax keyword length.
" https://twitter.com/dictav/status/287435117469761536
let g:neocomplete#sources#syntax#min_keyword_length = 3
let g:neocomplete#auto_completion_start_length = 3
let g:neocomplete#lock_buffer_name_pattern = '\*ku\*'

" 日本語入力中に補完されると日本語が打ち切れない（意味ない？）
let g:neocomplete#lock_iminsert = 1


" Define dictionary.
let g:neocomplete#sources#dictionary#dictionaries = {
    \ 'default' : '',
    \ 'vimshell' : $HOME.'/.vimshell_hist',
    \ 'scheme' : $HOME.'/.gosh_completions'
        \ }

" Define keyword.
if !exists('g:neocomplete#keyword_patterns')
    let g:neocomplete#keyword_patterns = {}
endif

"日本語を補完候補として取得しないようにする
let g:neocomplete#keyword_patterns['default'] = '\h\w*'

let g:neocomplete#cursor_hold_i_time = 1500




" Plugin key-mappings.
inoremap <expr><C-g>     neocomplete#undo_completion()
inoremap <expr><C-Space>     neocomplete#start_manual_complete()

" Recommended key-mappings.
" <CR>: close popup and save indent.
" inoremap <silent> <TAB> <C-r>=<SID>my_tab_function()<CR>
" function! s:my_tab_function()
  " return pumvisible() ? neocomplete#close_popup() : "\<TAB>"
" endfunction
" imap <silent> <CR> <C-r>=<SID>my_cr_function()<CR>
" imap <expr> <CR> pumvisible() ? neocomplete#close_popup() : "\<Plug>(smartinput_CR)"
      " " \ neocomplete#close_popup() : "\<Plug>(smartinput_CR)"
" function! s:my_cr_function()
  " return pumvisible() ? neocomplete#close_popup() : "\<Plug>(smartinput_CR)"
" endfunction
" <C-h>, <BS>: close popup and delete backword char.
" inoremap <expr><C-h> neocomplete#smart_close_popup()."\<C-h>"
" inoremap <expr><BS> neocomplete#smart_close_popup()."\<C-h>"
" plugin内で使われているので必須
inoremap <expr><C-y>  neocomplete#close_popup()
" inoremap <expr><C-e>  neocomplete#cancel_popup()
" Close popup by <Space>.
"inoremap <expr><Space> pumvisible() ? neocomplete#close_popup() : "\<Space>"

" For cursor moving in insert mode(Not recommended)
" inoremap <expr><Left>  neocomplete#close_popup() . "\<Left>"
" inoremap <expr><Right> neocomplete#close_popup() . "\<Right>"
" inoremap <expr><Up>    neocomplete#close_popup() . "\<Up>"
" inoremap <expr><Down>  neocomplete#close_popup() . "\<Down>"
" Or set this.
let g:neocomplete#enable_cursor_hold_i = 1
" Or set this.
" let g:neocomplete#enable_insert_char_pre = 1

" AutoComplPop like behavior.
"let g:neocomplete#enable_auto_select = 1

" Shell like behavior(not recommended).
"set completeopt+=longest
let g:neocomplete#enable_auto_select = 1
"let g:neocomplete#disable_auto_complete = 1
"inoremap <expr><TAB>  pumvisible() ? "\<Down>" : "\<C-x>\<C-u>"

" Enable omni completion.
autocmd vimrc FileType css setlocal omnifunc=csscomplete#CompleteCSS
autocmd vimrc FileType html,markdown setlocal omnifunc=htmlcomplete#CompleteTags
autocmd vimrc FileType javascript setlocal omnifunc=javascriptcomplete#CompleteJS
autocmd vimrc FileType python setlocal omnifunc=pythoncomplete#Complete
autocmd vimrc FileType xml setlocal omnifunc=xmlcomplete#CompleteTags

" Enable heavy omni completion.
if !exists('g:neocomplete#sources#omni#input_patterns')
  let g:neocomplete#sources#omni#input_patterns = {}
endif
"let g:neocomplete#sources#omni#input_patterns.php = '[^. \t]->\h\w*\|\h\w*::'
"let g:neocomplete#sources#omni#input_patterns.c = '[^.[:digit:] *\t]\%(\.\|->\)'
"let g:neocomplete#sources#omni#input_patterns.cpp = '[^.[:digit:] *\t]\%(\.\|->\)\|\h\w*::'

" For perlomni.vim setting.
" https://github.com/c9s/perlomni.vim
let g:neocomplete#sources#omni#input_patterns.perl = '\h\w*->\h\w*\|\h\w*::'

" Multiple_cursorsとの競合の対応
" https://github.com/terryma/vim-multiple-cursors/pull/65
" function! Multiple_cursors_before()
    " exe 'NeoCompleteLock'
    " echo 'Disabled autocomplete'
" endfunction

" function! Multiple_cursors_after()
    " exe 'NeoCompleteUnlock'
    " echo 'Enabled autocomplete'
" endfunction
" Called once right before you start selecting multiple cursors
" function! Multiple_cursors_before()
  " if exists(':NeoCompleteLock')==2
    " exe 'NeoCompleteLock'
  " endif
" endfunction

" Called once only when the multiple selection is canceled (default <Esc>)
" function! Multiple_cursors_after()
  " if exists(':NeoCompleteUnlock')==2
    " exe 'NeoCompleteUnlock'
  " endif
" endfunction



" Settings for neosnippet"
" Plugin key-mappings.
" imap <C-k>     <Plug>(neosnippet_expand_or_jump)
smap <C-k>     <Plug>(neosnippet_expand_or_jump)
xmap <C-k>     <Plug>(neosnippet_expand_target)

" SuperTab like snippets behavior.
imap <expr><TAB> neosnippet#expandable_or_jumpable() ?
\ "\<Plug>(neosnippet_expand_or_jump)"
\: pumvisible() ? "\<C-n>" : "\<TAB>"

smap <expr><TAB> neosnippet#expandable_or_jumpable() ?
\ "\<Plug>(neosnippet_expand_or_jump)"
\: "\<TAB>"

" For snippet_complete marker.
if has('conceal')
  set conceallevel=2 concealcursor=i
endif
" http://d.hatena.ne.jp/osyo-manga/20140820/1408546674
autocmd InsertLeave * syntax clear neosnippetConcealExpandSnippets

" Tell Neosnippet about the other snippets
" let g:neosnippet#snippets_directory='~/.vim/bundle/vim-snippets/snippets'
let g:neosnippet#snippets_directory='~/.vim/snippets'


let g:user_emmet_leader_key='<C-Z>'
" let g:user_emmet_leader_key='<c-x>'
let g:user_emmet_settings = {
\ 'variables': {
\ 'lang' : 'ja'
\ }
\}

" noremap <Leader>b :Autoformat<CR><CR>
" nnoremap <leader>b :%!js-beautify -j -q -B -f -<CR>
autocmd vimrc FileType javascript nmap <silent> <buffer> <Leader>b :JsBeautifySimple<cr>
autocmd vimrc FileType javascript vmap <silent> <buffer> <Leader>b :JsBeautifySimple<cr>
autocmd vimrc FileType javascript let b:JsBeautifySimple_config = "~/.jsbeautifyrc"

" https://github.com/jelera/vim-javascript-syntax
" au FileType javascript call JavaScriptFold()

" http://layzie.hatenablog.com/entry/20130122/1358811539
" この設定入れるとshiftwidthを1にしてインデントしてくれる
let g:SimpleJsIndenter_BriefMode = 1
" この設定入れるとswitchのインデントがいくらかマシに
let g:SimpleJsIndenter_CaseIndentLevel = -1

let g:jsdoc_default_mapping = 0
" nnoremap <silent> <Leader>d :JsDoc<CR>

nnoremap <silent> <Leader>gb :Gblame<CR>
nnoremap <silent> <Leader>gd :Gdiff<CR>
nnoremap <silent> <Leader>gs :Gstatus<CR>
nnoremap <silent> <Leader>ga :Gwrite<CR>
nnoremap <silent> <Leader>gc :Gcommit<CR>
nnoremap <silent> <Leader>gr :Gremove<CR>
nnoremap <silent> <Leader>gm :Gmove<CR>
nnoremap <silent> <Leader>gr :Gread<CR>

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
let g:brightest#highlight = {
\   "group" : "BrightestUnderline"
\}

map /  <Plug>(incsearch-forward)
map ?  <Plug>(incsearch-backward)
" どうもincsearchは日本語が打てないようなので最悪これで
nnoremap <Leader>/ /
nnoremap <Leader>? ?
" map g/ <Plug>(incsearch-stay)

"" for hl_matchit
let g:hl_matchit_enable_on_vim_startup = 1
let g:hl_matchit_hl_groupname = 'Title'
let g:hl_matchit_allow_ft = 'html\|vim\|ruby\|sh'

" http://d.hatena.ne.jp/oppara/20111229/p1
" phpStylist.php へのパス
let g:phpstylist_cmd_path = $HOME.'/Desktop/repository/SettingFiles/bin/phpStylist.php'

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
" let g:easy_align_delimiters = {
" \ '/': { 'pattern': '//\+', 'delimiter_align': 'l', 'ignore_groups': ['!Comment'] }
" \ }
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


" http://cohama.hateblo.jp/entry/20130517/1368806202

" これは外に定義!
function! s:gitv_get_current_hash()
  return matchstr(getline('.'), '\[\zs.\{7\}\ze\]$')
endfunction

autocmd FileType git setlocal nofoldenable foldlevel=0
function! s:toggle_git_folding()
  if &filetype ==# 'git'
    setlocal foldenable!
  endif
endfunction

autocmd FileType gitv call s:my_gitv_settings()
function! s:my_gitv_settings()
  " ここに設定を書く
  setlocal iskeyword+=/,-,.
  nnoremap <silent><buffer> C :<C-u>Git checkout <C-r><C-w><CR>
  nnoremap <buffer> <Leader>rb :<C-u>Git rebase <C-r>=GitvGetCurrentHash()<CR><Space>
  nnoremap <buffer> <Leader>R :<C-u>Git revert <C-r>=GitvGetCurrentHash()<CR><CR>
  nnoremap <buffer> <Leader>h :<C-u>Git cherry-pick <C-r>=GitvGetCurrentHash()<CR><CR>
  nnoremap <buffer> <Leader>rh :<C-u>Git reset --hard <C-r>=GitvGetCurrentHash()<CR>
  nnoremap <silent><buffer> t :<C-u>windo call <SID>toggle_git_folding()<CR>1<C-w>w
endfunction


" http://win-to-mac.blogspot.jp/2012/08/vim.html
" set statusline=%<%f\ %m%r%h%w%{'['.(&fenc!=''?&fenc:&enc).']['.&ff.']'}%=%l,%c%V%8P

" for WordCount
" https://github.com/fuenor/vim-wordcount
" set statusline+=[wc:%{WordCount()}]

" (percentage, line number, column number)
let g:airline_section_z = 'l:%l/%L|c:%c|wc:%{WordCount()}|%P'
set updatetime=500

" (bufferline or filename)
let g:airline_section_c = '%{getcwd()} | %t'

" call smartinput_endwise#define_default_rules()

nmap p <Plug>(yankround-p)
xmap p <Plug>(yankround-p)
nmap P <Plug>(yankround-P)
nmap gp <Plug>(yankround-gp)
xmap gp <Plug>(yankround-gp)
nmap gP <Plug>(yankround-gP)
" M-p
nmap π <Plug>(yankround-prev)
 " M-n
nmap ˜ <Plug>(yankround-next)


" for Changed
let g:Changed_definedSigns = 1
sign define SIGN_CHANGED_DELETED_VIM text=- texthl=ChangedDeleteHl
sign define SIGN_CHANGED_ADDED_VIM   text=+ texthl=ChangedAddHl
sign define SIGN_CHANGED_VIM         text=* texthl=ChangedDefaultHl

let g:easytags_events = ['BufWritePost']
let g:easytags_async = 1

" http://qiita.com/tutu/items/fbc4023ebc3004964e86
noremap <Leader>tv :vsp<CR> :exe("tjump ".expand('<cword>'))<CR>
noremap <Leader>ts :split<CR> :exe("tjump ".expand('<cword>'))<CR>
nmap <Leader>tp vas<C-w>}
noremap <Leader>tq <C-w><C-z>
nmap <Leader>tn vas<C-]>
noremap <Leader>tb <C-t>

" http://blog.supermomonga.com/articles/vim/share-cr-map-with-multiple-plugins.html
if neobundle#tap('vim-smartinput')
  function! neobundle#tapped.hooks.on_post_source(bundle)
    " neosnippet and neocomplete compatible
    call smartinput#map_to_trigger('i', '<Plug>(vimrc_cr)', '<Enter>', '<Enter>')
    imap <expr><CR> !pumvisible() ? "\<Plug>(vimrc_cr)" :
          \ neosnippet#expandable() ? "\<Plug>(neosnippet_expand)" :
          \ neocomplete#close_popup()
  endfunction
  call neobundle#untap()
endif

nnoremap <silent> <Leader>d :filetype detect<CR>
let g:scratchBackupFile=$HOME . "~/.backup/vim/scratch.txt"

" http://deris.hatenablog.jp/entry/20120818/1345291162
" let g:execcmd_after_ftplugin = {
  " \    '_': [
  " \        'setlocal fo-=r fo-=o fo-=c',
  " \    ],
  " \}

nnoremap <F7> :VimShell -toggle -split<CR>
inoremap <F7> <C-o>:VimShell -toggle -split<CR>
nnoremap <Leader>qp :QuickRun php<CR>
nnoremap <Leader>qr :QuickRun ruby<CR>

let g:gitgutter_map_keys = 0
let g:gitgutter_eager = 0
