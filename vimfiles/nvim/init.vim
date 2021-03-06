"NeoVim Settings for CUI
if !exists('g:setting_files_path')
  let g:setting_files_path = $HOME.'/Desktop/repository/SettingFiles' | lockvar! setting_files_path
  let g:vim_dir_path = g:setting_files_path . '/vimfiles' | lockvar! vim_dir_path
endif

" http://stackoverflow.com/questions/840900/vim-sourcing-based-on-a-string/841025#841163
exec 'source ' .  g:setting_files_path . '/vimfiles/.vimrc.common'

let s:dein_dir = g:vim_dir_path . '/dein/nvim'
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
  " call dein#call_hook('source')
endif

" もし、未インストールものものがあったらインストール
if dein#check_install()
  call dein#install()
endif

" for NERDCommenter
filetype plugin on

" 改行で自動コメントアウトを無効にする
set formatoptions-=ro

" タブ設定
" http://thinca.hatenablog.com/entry/20111204/1322932585
" タブページを常に表示
set showtabline=2
" gVimでもテキストベースのタブページを使う
set guioptions-=e
function! MakeTabLine()
  let titles = map(range(1, tabpagenr('$')), 's:tabpage_label(v:val)')
  let sep = ' | '  " タブ間の区切り
  let tabpages = join(titles, sep) . sep . '%#TabLineFill#%T'
  let info = ''  " 好きな情報を入れる
  return tabpages . '%=' . info  " タブリストを左に、情報を右に表示
endfunction

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
  let mod = len(filter(copy(bufnrs), 'getbufvar(v:val, "&modified")')) ? '[+]' : ''
  let sp = (no . mod) ==# '' ? '' : ' '  " 隙間空ける

  " カレントバッファ
  let curbufnr = bufnrs[tabpagewinnr(a:n) - 1]  " tabpagewinnr() は 1 origin
  let fname = pathshorten(bufname(curbufnr))
  if fname ==# ''
    " バッファ名がなければ No title としておきます。ここではマルチバイト文字を使わないほうが無難です
    let fname = 'No title'
  endif

  let label = no . mod . sp . fname

  return '%' . a:n . 'T' . hi . label . '%T%#TabLineFill#'
endfunction

" Netrw設定
" netrwは常にtree view
let g:netrw_liststyle = 3
" ヘッダを非表示にする
let g:netrw_banner=0
" サイズを(K,M,G)で表示する
let g:netrw_sizestyle="H"
" 日付フォーマットを yyyy/mm/dd(曜日) hh:mm:ss で表示する
let g:netrw_timefmt="%Y/%m/%d(%a) %H:%M:%S"
" プレビューウィンドウを垂直分割で表示する
let g:netrw_preview=1
" 'v'でファイルを開くときは右側に開く。(デフォルトが左側なので入れ替え)
let g:netrw_altv = 1
" " 'o'でファイルを開くときは下側に開く。(デフォルトが上側なので入れ替え)
let g:netrw_alto = 1
nnoremap <Leader>f :Ve<CR>
" inoremap <Leader>f <ESC>:Ve<CR>

" Theme設定
" syntax enable
syntax on
" GUI設定
" if (has("termguicolors"))
 " set termguicolors
" endif
" colorscheme molokai
colorscheme solarized8

" キーバインド
" NEDRCommenter
nmap ,, <Plug>NERDCommenterToggle
vmap ,, <Plug>NERDCommenterToggle

" vimでファイルを開いたときに、tmuxのwindow名にファイル名を表示
" if exists('$TMUX') && !exists('$NORENAME')
  " au BufEnter * if empty(&buftype) | call system('tmux rename-window "[vim]"'.expand('%:t:S')) | endif
  " au VimLeave * call system('tmux set-window automatic-rename on')
" endif

" vimrcをリロード
" http://whileimautomaton.net/2008/07/20150335
" nnoremap <Space>s  :<C-u>source $VIMRC<Return>
" nnoremap <Leader>s  :<C-u>source g:vim_dir_path . '/init.vim' <Return>
nnoremap <Leader>s  :<C-u>source ~/.config/nvim/init.vim <Return>
" command! ReloadVimrc  :source ~/.vimrc

function! DeinCacheClear()
  :call map(dein#check_clean(), "delete(v:val, 'rf')")
  :call dein#recache_runtimepath()
  :echo 'dein cache cleared!'
endfunction
command! DeinCacheClear :call DeinCacheClear()
nnoremap <silent> <Leader>c :call DeinCacheClear()<CR>

if exists('g:vv')
  VVset fontsize=13
  VVset lineheight=1.3
  VVset reloadchanged=1
  VVset fontfamily='Monaco'
endif
