return {
  'kevinhwang91/nvim-hlslens',
  config = function()
    require("scrollbar.handlers.search").setup({
      require('hlslens').setup({
        calm_down = true,
        nearest_only = true,
      })
    })
  end,
}
