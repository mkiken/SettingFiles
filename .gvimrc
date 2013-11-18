" Vim Settings for GUI

" カラースキーマを設定
colorscheme molokai


" ツールバー非表示
set guioptions-=T

let OSTYPE = system('uname')
if OSTYPE == "Darwin\n"
	""ここにMac向けの設定
	set transparency=2 " (不透明 0〜100 透明)
	set guifont=Monaco:h13
	set guifontwide=Monaco:h13
" set guifont=Courier:h14
" set guifontwide=Courier:h14
	" http://vim-users.jp/2011/10/hack234/
	"augroup hack234
	"  autocmd!
	if has('mac')
		autocmd FocusGained * set transparency=2
		autocmd FocusLost * set transparency=5
	endif
	"augroup END

	" highlight Cursor guifg=#000d18 guibg=#8faf9f gui=bold
	" highlight CursorIM guifg=NONE guibg=#ecbcbc



elseif OSTYPE == "Linux\n"
	""ここにLinux向けの設定
	set guifont=DejaVu\ Sans\ Mono\ 10
	" set guifontwide=Monospace:h13
	set lines=50 columns=150

endif


" set lines=50 columns=150

"## IME状態に応じたカーソル色を設定
" http://mba-hack.blogspot.jp/2012/09/vim.html
highlight Cursor guifg=#000d18 guibg=#8faf9f gui=bold
highlight CursorIM guifg=NONE guibg=#ecbcbc

""""""""""""""""""""""""""""""
"挿入モード時、ステータスラインの色を変更
""""""""""""""""""""""""""""""
let g:hi_insert = 'highlight StatusLine guifg=darkblue guibg=gray gui=none ctermfg=blue ctermbg=yellow cterm=none'

if has('syntax')
	augroup InsertHook
		autocmd!
		autocmd InsertEnter * call s:StatusLine('Enter')
		autocmd InsertLeave * call s:StatusLine('Leave')
	augroup END
endif

let s:slhlcmd = ''
function! s:StatusLine(mode)
	if a:mode == 'Enter'
		silent! let s:slhlcmd = 'highlight ' . s:GetHighlight('StatusLine')
		silent exec g:hi_insert
	else
		highlight clear StatusLine
		silent exec s:slhlcmd
	endif
endfunction

function! s:GetHighlight(hi)
	redir => hl
	exec 'highlight '.a:hi
	redir END
	let hl = substitute(hl, '[\r\n]', '', 'g')
	let hl = substitute(hl, 'xxx', '', '')
	return hl
endfunction
