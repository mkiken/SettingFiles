return {
  'nvim-tree/nvim-tree.lua',
  requires = {
    'nvim-tree/nvim-web-devicons'
  },
  config = true,
  keys = {
    {mode = "n", "<leader>t", "<cmd>NvimTreeToggle<CR>", desc = "NvimTreeをトグルする"},
  }
}
