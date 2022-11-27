-- lua/custom/mappings 
local M = {}

-- add this table only when you want to disable default keys
-- 無効化するデフォルトのキーマッピング
M.disabled = {
  -- i = { -- インサートモードに関するキーマッピング
  --   ["<C-b>"] = "", -- { "<ESC>^i", "beginning of line" },
  --   ["<C-e>"] = "", -- { "<End>", "end of line" },
  --   ["<C-h>"] = "", -- { "<Left>", "move left" },
  --   ["<C-l>"] = "", -- { "<Right>", "move right" },
  --   ["<C-j>"] = "", -- { "<Down>", "move down" },
  --   ["<C-k>"] = "", -- { "<Up>", "move up" },
  -- }

  n = { -- ノーマルモードに関するキーマッピング
    ["<C-s>"] = "", -- { "<cmd> w <CR>", "save file" },
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
  },
}

-- Let's override nvimtree's mappings
M.nvimtree = {
   n = {
      ["<leader>f"] = { "<cmd> NvimTreeToggle <CR>", "   toggle nvimtree" },
      -- ["<C-n>"] = { "<cmd> Telescope <CR>", "open telescope" },
   },
}

M.tabufline = {
  plugin = true,

  n = {
    -- cycle through buffers
    ["gt"] = {
      function()
        require("nvchad_ui.tabufline").tabuflineNext()
      end,
      "goto next buffer",
    },

    ["gT"] = {
      function()
        require("nvchad_ui.tabufline").tabuflinePrev()
      end,
      "goto prev buffer",
    },
  },
}

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

return M
