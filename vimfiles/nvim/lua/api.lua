-- http://rbtnn.hateblo.jp/entry/2014/11/30/17474
-- autocmd グループを定義
vim.api.nvim_create_augroup("vimrc", { clear = true })

-- 改行で自動コメントアウトを無効にする
vim.api.nvim_create_autocmd("FileType", {
  pattern = "*",
  callback = function()
      vim.opt_local.formatoptions:remove({ "c", "r", "o" })
  end,
})