" Vim Settings for GUI

" カラースキーマを設定
colorscheme molokai

set guifont=Monaco:h13
set guifontwide=Monaco:h13
" set guifont=Courier:h14
" set guifontwide=Courier:h14

set lines=35 columns=100
" ツールバー非表示
set guioptions-=T

set transparency=2 " (不透明 0〜100 透明)
" http://vim-users.jp/2011/10/hack234/
"augroup hack234
"  autocmd!
  if has('mac')
    autocmd FocusGained * set transparency=2
    autocmd FocusLost * set transparency=5
  endif
"augroup END

"## IME状態に応じたカーソル色を設定
" http://mba-hack.blogspot.jp/2012/09/vim.html
highlight Cursor guifg=#000d18 guibg=#8faf9f gui=bold
highlight CursorIM guifg=NONE guibg=#ecbcbc