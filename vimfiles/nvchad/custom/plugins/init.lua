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
}
