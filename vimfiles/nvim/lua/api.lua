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

-- yank時にハイライト
-- https://neovim.io/doc/user/lua.html#lua-highlight
vim.api.nvim_create_autocmd('TextYankPost', {
    callback = function()
        vim.highlight.on_yank({ higroup = 'Visual', timeout = 300 })
    end,
})

-- [Vim/Neovimをquitするときに特殊ウィンドウを一気に閉じる](https://zenn.dev/vim_jp/articles/ff6cd224fab0c7)
vim.api.nvim_create_autocmd('QuitPre', {
  callback = function()
    -- 現在のウィンドウ番号を取得
    local current_win = vim.api.nvim_get_current_win()
    -- すべてのウィンドウをループして調べる
    for _, win in ipairs(vim.api.nvim_list_wins()) do
      -- カレント以外を調査
      if win ~= current_win then
        local buf = vim.api.nvim_win_get_buf(win)
        -- buftypeが空文字（通常のバッファ）があればループ終了
        if vim.bo[buf].buftype == '' then
          return
        end
      end
    end
    -- ここまで来たらカレント以外がすべて特殊ウィンドウということなので
    -- カレント以外をすべて閉じる
    vim.cmd.only({ bang = true })
    -- この後、ウィンドウ1つの状態でquitが実行されるので、Vimが終了する
  end,
  desc = 'Close all special buffers and quit Neovim',
})