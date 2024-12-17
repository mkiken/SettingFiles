return {
  'kevinhwang91/nvim-hlslens',
  config = function()
    require("scrollbar.handlers.search").setup({
      require('hlslens').setup({
        calm_down = true,
        nearest_only = true,
      })
    })
    vim.keymap.set({'n', 'x'}, '<leader>L', function()
      vim.schedule(function()
        if require('hlslens').exportLastSearchToQuickfix() then
          vim.cmd('cw')
        end
      end)
      return ':noh<CR>'
    end, {expr = true})
  end,
}
