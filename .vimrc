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

" 行番号の表示
set number
" カーソルが何行目の何列目に置かれているかを表示する
set ruler
set title "編集中のファイル名を表示する


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


" for pathogen
execute pathogen#infect()
filetype plugin indent on

" for NERDCommenter
" http://qiita.com/items/b69b41ad4ea2497b3477
let NERDSpaceDelims = 1
nmap ,, <Plug>NERDCommenterToggle
vmap ,, <Plug>NERDCommenterToggle

map <Esc>f :NERDTreeToggle<CR>


autocmd BufNewFile,BufReadPost *.pegjs set filetype=pegjs
autocmd BufNewFile,BufReadPost *.language set filetype=pegjs
autocmd BufNewFile,BufReadPost *.grm set filetype=pegjs
