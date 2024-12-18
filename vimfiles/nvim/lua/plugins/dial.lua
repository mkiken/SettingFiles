return {
  "monaqa/dial.nvim",
  config = function()
    local dial = require("dial.map")
    local augend = require("dial.augend")

    -- 基本設定
    require("dial.config").augends:register_group {
      default = {
        augend.constant.new { elements = { "true", "false" }, cyclic = true },
        augend.integer.alias.decimal, -- 10進数
        augend.integer.alias.hex,    -- 16進数
        augend.date.alias["%Y/%m/%d"], -- 日付フォーマット
      },
    }

    -- キーマッピング例
    vim.keymap.set("n", "<C-a>", function()
      require("dial.map").manipulate("increment", "normal")
    end)
    vim.keymap.set("n", "<C-x>", function()
      require("dial.map").manipulate("decrement", "normal")
    end)
    vim.keymap.set("n", "g<C-a>", function()
      require("dial.map").manipulate("increment", "gnormal")
    end)
    vim.keymap.set("n", "g<C-x>", function()
      require("dial.map").manipulate("decrement", "gnormal")
    end)
    vim.keymap.set("v", "<C-a>", function()
      require("dial.map").manipulate("increment", "visual")
    end)
    vim.keymap.set("v", "<C-x>", function()
      require("dial.map").manipulate("decrement", "visual")
    end)
    vim.keymap.set("v", "g<C-a>", function()
      require("dial.map").manipulate("increment", "gvisual")
    end)
    vim.keymap.set("v", "g<C-x>", function()
      require("dial.map").manipulate("decrement", "gvisual")
    end)
  end,
}
