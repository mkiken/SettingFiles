-- lua/custom/mappings 
local M = {}

-- add this table only when you want to disable default keys
-- 無効化するデフォルトのキーマッピング
M.disabled = {
  n = { -- ノーマルモードに関するキーマッピング
    ["<C-s>"] = "", -- { "<cmd> w <CR>", "save file" },
    ["<TAB>"] = "", -- tabにマッピングするとC-iも引きずられるので無効化する
    ["<S-TAB>"] = "", -- tabと整合性を合わせる
  }
}

M.general = {
  i = {
    ["<C-a>"] = { "<Home>", "beginning of line" },
    ["<C-e>"] = { "<End>", "end of line" },
    ["<C-b>"] = { "<Left>", "move left" },
    ["<C-f>"] = { "<Right>", "move right" },
    ["<C-n>"] = { "<Down>", "move down" },
    ["<C-p>"] = { "<Up>", "move up" },
    ["<C-h>"] = { "<BackSpace>", "前1文字削除" },
    ["<C-d>"] = { "<Del>", "後1文字削除" },
    ["<C-k>"] = { "<c-o>D", "カーソルより後の文字を削除" },
  },
  n = {
    ["<leader>x"] = { "\"+x", "他のアプリケーションとのコピー" },
    ["<leader>y"] = { "\"+y", "他のアプリケーションとのコピー" },
    ["<leader>p"] = { "\"+p", "他のアプリケーションとのペースト" },
  },
  v = {
    [">"] = { ">gv", "visulaモードで選択してからのインデント調整で調整後に選択範囲を開放しない" },
    ["<"] = { "<gv", "visulaモードで選択してからのインデント調整で調整後に選択範囲を開放しない" },

    ["<leader>x"] = { "\"+x", "他のアプリケーションとのコピー" },
    ["<leader>y"] = { "\"+y", "他のアプリケーションとのコピー" },
  },
}

-- Let's override nvimtree's mappings
M.nvimtree = {
   n = {
      ["<leader>f"] = { "<cmd> NvimTreeToggle <CR>", "   toggle nvimtree" },
      -- ["<C-n>"] = { "<cmd> Telescope <CR>", "open telescope" },
   },
}

-- M.tabufline = {
--   plugin = false,
--
--   n = {
--     -- cycle through buffers
--     ["gt"] = {
--       function()
--         require("nvchad_ui.tabufline").tabuflineNext()
--       end,
--       "goto next buffer",
--     },
--
--     ["gT"] = {
--       function()
--         require("nvchad_ui.tabufline").tabuflinePrev()
--       end,
--       "goto prev buffer",
--     },
--   },
-- }

M.comment = {
  plugin = true,

  -- toggle comment in both modes
  n = {
    [",,"] = {
      function()
        require("Comment.api").toggle.linewise.current()
      end,
      "toggle comment",
    },
  },

  v = {
    [",,"] = {
      "<ESC><cmd>lua require('Comment.api').toggle.linewise(vim.fn.visualmode())<CR>",
      "toggle comment",
    },
  },
}

M.tabufline = {
  plugin = true,

  n = {
    -- cycle through buffers
    ["<leader><right>"] = {
      function()
        require("nvchad_ui.tabufline").tabuflineNext()
      end,
      "goto next buffer",
    },

    ["<leader><left>"] = {
      function()
        require("nvchad_ui.tabufline").tabuflinePrev()
      end,
      "goto prev buffer",
    },

    -- pick buffers via numbers
    ["<leader>l"] = { "<cmd> TbufPick <CR>", "Pick buffer" },

    -- close buffer + hide terminal buffer
    ["<leader>w"] = {
      function()
        require("nvchad_ui.tabufline").close_buffer()
      end,
      "close buffer",
    },
  },
}
return M
