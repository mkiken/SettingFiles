return {
  "mvllow/modes.nvim",
  config = function()
    require("modes").setup({
      line_opacity = 0.45,
      set_cursor = true,
      set_cursorline = true,
      set_number = true,
      set_signcolumn = true,
      ignore = { "NvimTree", "TelescopePrompt" },
    })
  end,
}
