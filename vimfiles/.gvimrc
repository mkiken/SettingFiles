" Vim Settings for GUI

" カラースキーマを設定
" colorscheme molokai
" colorscheme Tomorrow
" colorscheme Tomorrow-Night
" colorscheme Tomorrow-Night-Bright
" colorscheme Tomorrow-Night-Blue
" colorscheme Tomorrow-Night-Eighties
" colorscheme solarized
" colorscheme wombat
colorscheme hybrid
" colorscheme iceberg
" colorscheme github
" colorscheme grb256
" colorscheme hybrid-light
" colorscheme inkpot
" colorscheme jellybeans
" colorscheme sexy-railscasts
" colorscheme solarized
" colorscheme summerfruits256
" colorscheme wombat
" colorscheme BusyBee
" colorscheme badwolf
" colorscheme codeschool
" colorscheme lucius
" colorscheme zenburn
" colorscheme macvim

augroup gvimrc
  autocmd!
augroup END


" http://vim.1045645.n5.nabble.com/Random-color-scheme-at-start-td1165585.html
function! Load_random_colors()
	let mycolors = split(globpath(&rtp,"**/colors/*.vim"),"\n")
  exe 'so ' . mycolors[localtime() % len(mycolors)]
  unlet mycolors
endfunction
" call Load_random_colors()

" command! Load_random_colors call Load_random_colors()
command! LoadRandomColors call Load_random_colors()

" ツールバー非表示
set guioptions-=T

" http://doruby.kbmj.com/aisi/20091218/Vim__
" 個別のタブの表示設定をします
function! GuiTabLabel()
  " タブで表示する文字列の初期化をします
  let l:label = ''

  " タブに含まれるバッファ(ウィンドウ)についての情報をとっておきます。
  let l:bufnrlist = tabpagebuflist(v:lnum)

  " 表示文字列にバッファ名を追加します
  " パスを全部表示させると長いのでファイル名だけを使います 詳しくは help fnamemodify()
  let l:bufname = fnamemodify(bufname(l:bufnrlist[tabpagewinnr(v:lnum) - 1]), ':t')
  " バッファ名がなければ No title としておきます。ここではマルチバイト文字を使わないほうが無難です
  let l:label .= l:bufname == '' ? 'No title' : l:bufname

  " タブ内にウィンドウが複数あるときにはその数を追加します(デフォルトで一応あるので)
  let l:wincount = tabpagewinnr(v:lnum, '$')
  if l:wincount > 1
    let l:label .= '[' . l:wincount . ']'
  endif

  " このタブページに変更のあるバッファがるときには '[+]' を追加します(デフォルトで一応あるので)
  for bufnr in l:bufnrlist
    if getbufvar(bufnr, "&modified")
      let l:label .= ' +'
      break
    endif
  endfor

  " 表示文字列を返します
  return l:label
endfunction

" guitablabel に上の関数を設定します
" その表示の前に %N というところでタブ番号を表示させています
set guitablabel=%N:\ %{GuiTabLabel()}

" http://d.hatena.ne.jp/Minamo/20081124/1227553857
" hi NonText guibg=NONE guifg=DarkGreen
" hi SpecialKey guibg=NONE guifg=Gray40


let OSTYPE = system('uname')
if OSTYPE == "Darwin\n"
	""ここにMac向けの設定
	set transparency=2 " (不透明 0〜100 透明)
	set guifont=Monaco:h12
    " set guifont=Osaka-Mono:h14
	" set guifontwide=Monaco:h12
    " set guifontwide=ヒラギノ角ゴ\ StdN\ W8:h14
    " set guifontwide=Osaka:h12
    set guifontwide=Osaka-Mono:h13

" set guifont=Courier:h14
" set guifontwide=Courier:h14
	" http://vim-users.jp/2011/10/hack234/
	"augroup hack234
	"  autocmd!
	if has('mac')
		autocmd gvimrc FocusGained * set transparency=5
		autocmd gvimrc FocusLost * set transparency=10
		" set lines=50 columns=150
	endif
	"augroup END

	" highlight Cursor guifg=#000d18 guibg=#8faf9f gui=bold
	" highlight CursorIM guifg=NONE guibg=#ecbcbc



elseif OSTYPE == "Linux\n"
	""ここにLinux向けの設定
	set guifont=DejaVu\ Sans\ Mono\ 10
	" set guifontwide=Monospace:h13
	" set lines=50 columns=150

endif


" set lines=50 columns=150

"## IME状態に応じたカーソル色を設定
" http://mba-hack.blogspot.jp/2012/09/vim.html
highlight Cursor guifg=#000d18 guibg=#8faf9f gui=bold
highlight CursorIM guifg=NONE guibg=#ecbcbc


" Window sizeの保存
" http://vim-users.jp/2010/01/hack120/
let g:save_window_file = expand('~/.backup/vim/.vimwinpos')
augroup SaveWindow
  autocmd!
  autocmd gvimrc VimLeavePre * call s:save_window()
  function! s:save_window()
    let options = [
      \ 'set columns=' . &columns,
      \ 'set lines=' . &lines,
      \ 'winpos ' . getwinposx() . ' ' . getwinposy(),
      \ ]
    call writefile(options, g:save_window_file)
  endfunction
augroup END

if filereadable(g:save_window_file)
  execute 'source' g:save_window_file
else
	set lines=50 columns=150
endif

highlight ChangedAddHl cterm=bold ctermbg=NONE ctermfg=green gui=bold guibg=NONE guifg=green
highlight ChangedDeleteHl cterm=bold ctermbg=NONE ctermfg=red gui=bold guibg=NONE guifg=red
highlight ChangedDefaultHl cterm=bold ctermbg=NONE ctermfg=yellow gui=bold guibg=NONE guifg=yellow
