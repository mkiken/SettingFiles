return {
  'nvimdev/indentmini.nvim',
  config = function()
    require('indentmini').setup({
      char = '┆',
      only_current = true,
    })
    -- Colors are applied automatically based on user-defined highlight groups.
    -- There is no default value.
    -- vim.cmd.highlight('IndentLine guifg=#123456')
    -- Current indent line highlight
    vim.cmd.highlight('IndentLineCurrent guifg=gray')
end,
}
