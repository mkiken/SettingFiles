" Vim Settings for GUI

" カラースキーマを設定
colorscheme molokai

set guifont=Monaco:h13

set lines=35 columns=100
" ツールバー非表示
set guioptions-=T

"set transparency=5 " (不透明 0〜100 透明)
" http://vim-users.jp/2011/10/hack234/
augroup hack234
  autocmd!
  if has('mac')
    autocmd FocusGained * set transparency=5
    autocmd FocusLost * set transparency=30
  endif
augroup END