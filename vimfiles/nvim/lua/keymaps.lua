-- リーダーキーを設定
vim.g.mapleader = " "

-- カーソルを表示行で移動する。物理行移動は <C-n>, <C-p>
if vim.g.vscode then
  -- vscode-neovimで gj, gk が独自定義されているので map で上書き
  vim.api.nvim_set_keymap('n', 'j', 'gj', { noremap = false })
  vim.api.nvim_set_keymap('n', 'k', 'gk', { noremap = false })
else
  -- 通常の Vim 設定
  vim.api.nvim_set_keymap('n', 'j', 'gj', { noremap = true, silent = true })
  vim.api.nvim_set_keymap('n', 'k', 'gk', { noremap = true, silent = true })
  vim.api.nvim_set_keymap('n', 'gj', 'j', { noremap = true, silent = true })
  vim.api.nvim_set_keymap('n', 'gk', 'k', { noremap = true, silent = true })
end

-- 下矢印キーで表示行単位の移動
vim.api.nvim_set_keymap('n', '<Down>', 'gj', { noremap = true, silent = true })
-- 上矢印キーで表示行単位の移動
vim.api.nvim_set_keymap('n', '<Up>', 'gk', { noremap = true, silent = true })

-- G を押した際にファイル終端に移動して End を実行
vim.api.nvim_set_keymap('n', 'G', 'G<End>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('v', 'G', 'G<End>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('o', 'G', 'G<End>', { noremap = true, silent = true })

-- 他のアプリケーションとのコピー＆ペースト
-- Visualモードでカット
vim.api.nvim_set_keymap('v', '<Leader>x', '"+x', { noremap = true, silent = true })
-- Visualモードでコピー
vim.api.nvim_set_keymap('v', '<Leader>y', '"+y', { noremap = true, silent = true })
-- ノーマルモードでペースト
vim.api.nvim_set_keymap('n', '<Leader>p', '"+p', { noremap = true, silent = true })

-- Visualモードで選択してからのインデント調整後に選択範囲を保持
vim.api.nvim_set_keymap('v', '>', '>gv', { noremap = true, silent = true })
vim.api.nvim_set_keymap('v', '<', '<gv', { noremap = true, silent = true })

-- カーソル移動のショートカット
vim.api.nvim_set_keymap('i', '<C-p>', '<Up>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('i', '<C-n>', '<Down>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('i', '<C-b>', '<Left>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('i', '<C-f>', '<Right>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('i', '<C-e>', '<End>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('i', '<C-a>', '<Home>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('i', '<C-d>', '<Del>', { noremap = true, silent = true })

-- カーソルより後の文字を削除
vim.api.nvim_set_keymap('i', '<C-k>', '<C-o>D', { noremap = true, silent = true })

-- アンドゥ操作
vim.api.nvim_set_keymap('i', '<C-u>', '<C-o>u', { noremap = true, silent = true })
vim.api.nvim_set_keymap('i', '<C-]>', '<C-o>u', { noremap = true, silent = true })
vim.api.nvim_set_keymap('i', '<C-r>', '<C-o><C-r>', { noremap = true, silent = true })

-- undo を区切る
-- http://haya14busa.com/vim-break-undo-sequence-in-insertmode/
vim.api.nvim_set_keymap('i', '<Space>', '<Space><C-g>u', { noremap = true, silent = true })

-- 設定ファイルの再読み込みキーマッピング
vim.keymap.set('n', '<Leader>s', function()
  vim.cmd('source ~/.config/nvim/init.lua')
  vim.notify('設定を再読み込みしました', vim.log.levels.INFO)
end, { silent = true })