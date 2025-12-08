return {
  'sunjon/shade.nvim',
  lazy = false,
  config = function()
    require('shade').setup({
      overlay_opacity = 50,  -- 0〜100 (高いほど暗い)
      opacity_step = 1,
      keys = {
        brightness_up    = '<C-Up>',
        brightness_down  = '<C-Down>',
        toggle           = '<Leader>s',
      }
    })
  end
}
