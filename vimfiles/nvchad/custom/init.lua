-- クリップボードはvimとOSは分ける
vim.opt.clipboard = ""
vim.opt.gdefault = true

-- autocmds
local autocmd = vim.api.nvim_create_autocmd

autocmd('BufEnter', {
  pattern = '.spacemacs',
  command = "set filetype=lisp"
})
