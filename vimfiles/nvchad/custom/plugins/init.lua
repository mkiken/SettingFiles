-- custom/plugins/init.lua
-- we're basically returning a table!
return {
  ["NvChad/ui"] = {
    override_options = {
      tabufline = {
        enabled = false,
        lazyload = true,
        overriden_modules = nil,
      },
    },
},
}
