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
-- カット
vim.api.nvim_set_keymap('n', '<Leader>c', '"+c', { noremap = true, silent = true })
vim.api.nvim_set_keymap('x', '<Leader>c', '"+c', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', '<Leader>C', '"+C', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', '<Leader>d', '"+d', { noremap = true, silent = true })
vim.api.nvim_set_keymap('x', '<Leader>d', '"+d', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', '<Leader>D', '"+D', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', '<Leader>x', '"+x', { noremap = true, silent = true })
vim.api.nvim_set_keymap('x', '<Leader>x', '"+x', { noremap = true, silent = true })
-- コピー
vim.api.nvim_set_keymap('n', '<Leader>y', '"+y', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', '<Leader>yy', '"+yy', { noremap = true, silent = true })
vim.api.nvim_set_keymap('x', '<Leader>y', '"+y', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', '<Leader>Y', '"+y$', { noremap = true, silent = true })
-- ペースト
vim.api.nvim_set_keymap('n', '<Leader>p', '"+p', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', '<Leader>P', '"+P', { noremap = true, silent = true })
vim.api.nvim_set_keymap('x', '<Leader>p', '"+p', { noremap = true, silent = true })
vim.api.nvim_set_keymap('x', '<Leader>P', '"+P', { noremap = true, silent = true })

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

-- undo を区切る(全部入り設定)
-- http://haya14busa.com/vim-break-undo-sequence-in-insertmode/
local undo_break_keys = {
  '<Space>', '<CR>',            -- 基本
  ',', '.', '!', '?',           -- 句読点・記号
  '(', ')', '[', ']', '{', '}', -- 括弧類
  '-', '_', ':', ';',           -- ハイフン/コロン類
  '"', "'"                      -- 引用符
}
for _, key in ipairs(undo_break_keys) do
  vim.keymap.set('i', key, key .. '<C-g>u', { noremap = true, silent = true })
end

-- Backspaceでもundo区切り(先にブレークポイントを挿入)
vim.keymap.set('i', '<BS>', '<C-g>u<BS>', { noremap = true, silent = true })

-- Escapeを2回押して:nohlsearch
vim.api.nvim_set_keymap('n', '<Esc><Esc>', ':nohlsearch<CR>', { noremap = true, silent = true })

-- バッファ移動
vim.api.nvim_set_keymap('n', 'gt', ':bnext<CR>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', 'gT', ':bprev<CR>', { noremap = true, silent = true })

-- タブ移動
vim.api.nvim_set_keymap('n', 'ge', ':tabnext<CR>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', 'gE', ':tabprev<CR>', { noremap = true, silent = true })

-- 設定ファイルの再読み込みキーマッピング
vim.keymap.set('n', '<Leader>s', function()
  vim.cmd('source ~/.config/nvim/init.lua')
  vim.notify('設定を再読み込みしました', vim.log.levels.INFO)
end, { silent = true })

local function count_pattern(text, pattern)
  local _, count = text:gsub(pattern, "")
  return count
end

local function trim_url(url)
  local always_trim = {
    ["."] = true,
    [","] = true,
    [";"] = true,
    [":"] = true,
    ["!"] = true,
    ["?"] = true,
    ["'"] = true,
    ['"'] = true,
    ["`"] = true,
  }
  local bracket_pairs = {
    [")"] = { "%(", "%)" },
    ["]"] = { "%[", "%]" },
    ["}"] = { "{", "}" },
  }

  while url ~= "" do
    local last_char = url:sub(-1)

    if always_trim[last_char] then
      url = url:sub(1, -2)
    elseif bracket_pairs[last_char] then
      local pair = bracket_pairs[last_char]
      if count_pattern(url, pair[2]) > count_pattern(url, pair[1]) then
        url = url:sub(1, -2)
      else
        break
      end
    else
      break
    end
  end

  return url
end

local function collect_buffer_urls()
  local urls = {}
  local seen = {}
  local lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)

  for _, line in ipairs(lines) do
    for match in line:gmatch("https?://[^%s<>'\"`]+") do
      local url = trim_url(match)
      if url:match("^https?://.+") and not seen[url] then
        seen[url] = true
        table.insert(urls, url)
      end
    end
  end

  return urls
end

local function open_url(url)
  local _, err = vim.ui.open(url)
  if err then
    vim.notify(("URLを開けませんでした: %s"):format(err), vim.log.levels.ERROR)
  end
end

local function select_buffer_url(urls)
  local has_pickers, pickers = pcall(require, "telescope.pickers")
  local has_finders, finders = pcall(require, "telescope.finders")
  local has_conf, conf = pcall(require, "telescope.config")
  local has_actions, actions = pcall(require, "telescope.actions")
  local has_action_state, action_state = pcall(require, "telescope.actions.state")

  if not (has_pickers and has_finders and has_conf and has_actions and has_action_state) then
    vim.ui.select(urls, { prompt = "Open URL" }, function(choice)
      if choice then
        open_url(choice)
      end
    end)
    return
  end

  pickers.new({}, {
    prompt_title = "Open URL",
    finder = finders.new_table({ results = urls }),
    sorter = conf.values.generic_sorter({}),
    attach_mappings = function(prompt_bufnr)
      actions.select_default:replace(function()
        local selection = action_state.get_selected_entry()
        actions.close(prompt_bufnr)

        if selection then
          open_url(selection.value)
        end
      end)

      return true
    end,
  }):find()
end

local function open_buffer_url()
  local urls = collect_buffer_urls()

  if #urls == 0 then
    vim.notify("現在のバッファにURLがありません", vim.log.levels.WARN)
    return
  end

  select_buffer_url(urls)
end

vim.api.nvim_create_user_command("OpenBufferUrl", open_buffer_url, {
  desc = "Open URL from current buffer",
})

vim.keymap.set("n", "<Leader>o", open_buffer_url, {
  silent = true,
  desc = "Open URL from current buffer",
})
