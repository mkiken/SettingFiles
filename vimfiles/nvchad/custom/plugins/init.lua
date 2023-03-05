-- custom/plugins/init.lua
-- we're basically returning a table!
return {
  ["NvChad/ui"] = {
    override_options = {
      tabufline = {
        -- enabled = true,
        lazyload = false,
        -- overriden_modules = nil,
      },
    },
  },

  ["kylechui/nvim-surround"] = {
    tag = "*",
    config = function()
      require("nvim-surround").setup()
    end,
  },

  -- dim inactive windows
  ["sunjon/shade.nvim"] = {
    config = function()
      require("shade").setup({
        overlay_opacity = 50,
        opacity_step = 1,
        keys = {
          -- brightness_up    = '<C-Up>',
          -- brightness_down  = '<C-Down>',
          -- toggle           = '<Leader>s',
        }
      })
    end,
  },
}
