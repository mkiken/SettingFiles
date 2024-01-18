-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here

---- ノーマルモード ----
vim.keymap.set("n", "<leader>x", '"+x', { desc = "他のアプリケーションとのコピー" })
vim.keymap.set("n", "<leader>y", '"+y', { desc = "他のアプリケーションとのコピー" })
vim.keymap.set("n", "<leader>p", '"+p', { desc = "他のアプリケーションとのペースト" })

-- cはnvimのデフォルトの挙動にしたい
vim.keymap.del("n", "c")

---- インサートモード ----
-- emacs的な挙動
vim.keymap.set("i", "<C-a>", "<Home>", { desc = "beginning of line" })
vim.keymap.set("i", "<C-e>", "<End>", { desc = "end of line" })
vim.keymap.set("i", "<C-b>", "<Left>", { desc = "move left" })
vim.keymap.set("i", "<C-f>", "<Right>", { desc = "move right" })
vim.keymap.set("i", "<C-n>", "<Down>", { desc = "move down" })
vim.keymap.set("i", "<C-p>", "<Up>", { desc = "move up" })
vim.keymap.set("i", "<C-h>", "<BackSpace>", { desc = "前1文字削除" })
vim.keymap.set("i", "<C-d>", "<Del>", { desc = "後1文字削除" })
vim.keymap.set("i", "<C-k>", "<c-o>D", { desc = "カーソルより後の文字を削除" })

-- modes.nvimでc-cで色が変わらない問題対応
vim.keymap.set("i", "<c-c>", "<esc>")

---- ビジュアルモード ----

vim.keymap.set("v", "<leader>x", '"+x', { desc = "他のアプリケーションとのコピー" })
vim.keymap.set("v", "<leader>y", '"+y', { desc = "他のアプリケーションとのコピー" })

if vim.g.vscode then
  -- VSCode extension
else
  -- ordinary Neovim
  -- VSCodeだとバグる
  vim.keymap.set("v", "<C-o>", "<C-c><C-o>", { desc = "" })
  -- C-iとTABは同じ
  -- https://github.com/neovim/neovim/issues/20126
  vim.keymap.set("v", "<TAB>", "<C-c><C-i>", { desc = "" })
end
