" Vim Settings for GUI

" カラースキーマを設定
" colorscheme BusyBee
" colorscheme Tomorrow
" colorscheme Tomorrow-Night
" colorscheme Tomorrow-Night-Blue
" colorscheme Tomorrow-Night-Bright
" colorscheme Tomorrow-Night-Eighties
" colorscheme badwolf
" colorscheme codeschool
" colorscheme evening
" colorscheme github
" colorscheme grb256
" colorscheme hybrid
" colorscheme hybrid-light
" colorscheme iceberg
" colorscheme inkpot
colorscheme jellybeans
" colorscheme lucius
" colorscheme macvim
" colorscheme molokai
" colorscheme sexy-railscasts
" colorscheme slate
" colorscheme solarized
" colorscheme summerfruits256
" colorscheme wombat
" colorscheme zenburn

" set background=light
set background=dark

augroup gvimrc
  autocmd!
augroup END


" http://vim.1045645.n5.nabble.com/Random-color-scheme-at-start-td1165585.html
function! Load_random_colors()
	let mycolors = split(globpath(&rtp,"**/colors/*.vim"),"\n")
  exe 'so ' . mycolors[localtime() % len(mycolors)]
  unlet mycolors
endfunction

command! LoadRandomColors call Load_random_colors()

" ツールバー非表示
set guioptions-=T
" http://www.kaoriya.net/blog/2011/09/20110915/
set guioptions-=m
" gVimでもテキストベースのタブページを使う
" set guioptions-=e

" http://doruby.kbmj.com/aisi/20091218/Vim__
" 個別のタブの表示設定をします
function! GuiTabLabel()
  " タブで表示する文字列の初期化をします
  let l:label = ''

  " タブに含まれるバッファ(ウィンドウ)についての情報をとっておきます。
  let l:bufnrlist = tabpagebuflist(v:lnum)

  " 表示文字列にバッファ名を追加します
  " パスを全部表示させると長いのでファイル名だけを使います 詳しくは help fnamemodify()
  let l:_bufname = bufname(l:bufnrlist[tabpagewinnr(v:lnum) - 1])
  if l:_bufname ==# ''
    " バッファ名がなければ No title としておきます。ここではマルチバイト文字を使わないほうが無難です
    let l:bufname = 'No title'
  else
    " 空じゃなければ短縮
    let l:_pathname = fnamemodify(l:_bufname, ':~')
    let l:bufname_split = split(l:_pathname, '/')
    let l:bufname = len(l:bufname_split) >= 2 ? l:bufname_split[-1] . '/' . l:bufname_split[-2] : l:bufname_split[-1]
  endif

  let l:label .= l:bufname

  " タブ内にウィンドウが複数あるときにはその数を追加します(デフォルトで一応あるので)
  let l:wincount = tabpagewinnr(v:lnum, '$')
  if l:wincount > 1
    let l:label = '[' . l:wincount . ']' . l:label
  endif

  " このタブページに変更のあるバッファがあるときには '[+]' を追加します(デフォルトで一応あるので)
  for bufnr in l:bufnrlist
    if getbufvar(bufnr, "&modified")
      let l:label = '* ' . l:label
      break
    endif
  endfor

  " 表示文字列を返します
  return l:label
endfunction

" guitablabel に上の関数を設定します
" その表示の前に %N というところでタブ番号を表示させています
set guitablabel=%N:\ %{GuiTabLabel()}

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
		autocmd gvimrc FocusLost * set transparency=15
		" set lines=50 columns=150
	endif
	"augroup END

elseif OSTYPE == "Linux\n"
	""ここにLinux向けの設定
	set guifont=DejaVu\ Sans\ Mono\ 10
	" set guifontwide=Monospace:h13
	" set lines=50 columns=150

endif

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
