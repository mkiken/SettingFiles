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
