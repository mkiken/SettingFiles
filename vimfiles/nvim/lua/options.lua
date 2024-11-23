-- カラーリング
vim.opt.syntax = 'enable'
vim.opt.hlsearch = true

vim.opt.encoding = 'utf-8'

-- ミュートにする。
vim.opt.visualbell = true
vim.opt.errorbells = false

vim.opt.cursorline = true

vim.opt.title = true
vim.opt.showcmd = true
vim.opt.laststatus = 2


-- https://www.reddit.com/r/neovim/comments/ppv7vr/initvim_to_initlua_set_undo_backup_swp_folders/?rdt=46251
local prefix = vim.env.XDG_CONFIG_HOME or vim.fn.expand("~/.config")
vim.opt.undofile = true
vim.opt.undodir = { prefix .. "/nvim/.undo//"}

vim.opt.swapfile = true
vim.opt.directory = { prefix .. "/nvim/.swp//"}

vim.opt.backup = true
vim.opt.backupdir = {prefix .. "/nvim/.backup//"}

-- 行番号の表示
vim.opt.number = true

-- http://d.hatena.ne.jp/ruicc/20090615/1245086039
if vim.o.compatible then
  vim.o.compatible = false
end

-- http://vim-users.jp/2010/04/hack137/
-- オートインデントを有効にする（新しい行のインデントを現在の行と同じにする）
vim.o.autoindent = true
-- vim.o.copyindent = true
-- vim.o.preserveindent = true
-- C言語スタイルのインデント機能が有効
vim.o.cindent = true
-- タブに展開
vim.o.expandtab = true
-- タブが対応する空白の数
vim.o.tabstop = 2
-- タブやバックスペースの使用等の編集操作をするときに、タブが対応する空白の数
vim.o.softtabstop = 2
-- インデントの各段階に使われる空白の数
vim.o.shiftwidth = 2
-- vim.o.smartindent = true
-- 行頭の余白内で Tab を打ち込むと、'shiftwidth' の数だけインデントする
vim.o.smarttab = true

-- 自動改行しない
-- http://kaworu.jpn.org/kaworu/2007-07-29-1.php
vim.o.textwidth = 0

-- 閉じ括弧が入力されたとき、対応する括弧を表示する
vim.o.showmatch = true

-- % で移動する括弧の構成に <> を追加する
vim.o.matchpairs = vim.o.matchpairs .. ",<:>"

-- カーソルを行頭、行末で止まらないようにする
vim.o.whichwrap = "b,s,h,l,<,>,[,]"

-- コマンドライン補完を拡張モードにする
vim.o.wildmenu = true

-- コマンドモードでの補完設定
vim.o.wildmode = "list:full,longest:full"

-- 検索の時に大文字小文字を区別しない
vim.o.ignorecase = true
-- 最後まで検索したら先頭に戻る
vim.o.wrapscan = true
-- インクリメンタルサーチ(検索文字を打ち込むと即検索)
vim.o.incsearch = true
-- 検索文字列に大文字が含まれている場合は区別して検索する
vim.o.smartcase = true
-- 置換の時 g オプションをデフォルトで有効にする
vim.o.gdefault = true

-- ファイル内容が変更されると自動読み込みする
vim.o.autoread = true

-- vim.o.copyindent = true
-- vim.o.preserveindent = true

-- タブラインを常に表示
vim.o.showtabline = 2

-- http://shoken.hatenablog.com/entry/20120617/p
-- 新しいウィンドウを下に開く
vim.o.splitbelow = true
-- vim.o.splitright = true

-- _でも単語区切り
vim.opt.iskeyword:remove('_')

-- ambiwidth の設定
vim.opt.ambiwidth = 'double'

-- 80文字目にラインを表示
vim.opt.colorcolumn = '80'

-- スクロール時の余白を5行に
vim.opt.scrolloff = 5

-- http://rbtnn.hateblo.jp/entry/2014/11/30/17474
-- autocmd グループを定義
vim.api.nvim_create_augroup("vimrc", { clear = true })

-- リーダーキーを設定
vim.g.mapleader = " "

-- 現在のディレクトリを自動変更
vim.opt.autochdir = true
