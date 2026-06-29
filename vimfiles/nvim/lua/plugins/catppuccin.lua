return {
  "catppuccin/nvim",
  name = "catppuccin",
  priority = 1000,
  lazy = false,
  config = function()
    require("catppuccin").setup({
      flavour = "mocha",
      integrations = {
        treesitter = true,
        telescope = { enabled = true },
        gitsigns = true,
        bufferline = true,
        nvimtree = true,
        native_lsp = { enabled = true },
        noice = true,
        notify = true,
        which_key = true,
        flash = true,
        markdown = true,
      },
    })
    vim.cmd.colorscheme("catppuccin")
  end,
}
