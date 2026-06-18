return {
  "folke/which-key.nvim",
  event = "VeryLazy",
  opts = {
    defer = function(ctx)
      if vim.list_contains({ "d", "y" }, ctx.operator) then
        return true
      end

      return vim.list_contains({ "V", "<C-V>" }, ctx.mode)
    end,
  },
  keys = {
    {
      "<leader>?",
      function()
        require("which-key").show({ global = false })
      end,
      desc = "Buffer Local Keymaps (which-key)",
    },
  },
}
