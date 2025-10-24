local git_blame = require('gitblame')

return {
  'nvim-lualine/lualine.nvim',
  dependencies = { 'nvim-tree/nvim-web-devicons' },
  config = function()
    require('lualine').setup({
      options = { theme = 'onedark' },
      sections = {
        lualine_c = {
          {
            'filename',
            path = 1,  -- 0: ファイル名のみ, 1: 相対パス, 2: 絶対パス, 3: 絶対パス(~付き)
            shorting_target = 40,  -- パスを短縮する際の最小幅
          },
        },
        lualine_x = {
          {
            require("noice").api.status.message.get_hl,
            cond = require("noice").api.status.message.has,
          },
          {
            require("noice").api.status.command.get,
            cond = require("noice").api.status.command.has,
            color = { fg = "#ff9e64" },
          },
          {
            require("noice").api.status.mode.get,
            cond = require("noice").api.status.mode.has,
            color = { fg = "#ff9e64" },
          },
          {
            require("noice").api.status.search.get,
            cond = require("noice").api.status.search.has,
            color = { fg = "#ff9e64" },
          },
        },
      }
    })
  end
}
