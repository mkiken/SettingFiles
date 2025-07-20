local wezterm = require "wezterm"

local M = {}

function M.setup(config)
  -- Color scheme settings
  -- config.color_scheme = "Catppuccin Mocha"
  -- config.color_scheme = 'iceberg'
  -- config.color_scheme = 'Tomorrow Night'
  -- config.color_scheme = 'Tomorrow Night Bright'
  config.color_scheme = 'Tomorrow Night Eighties'
  -- config.color_scheme = 'Molokai'
  -- config.color_scheme = 'Monokai Remastered'
  -- config.color_scheme = 'Monokai Soda'
  -- config.color_scheme = 'Monokai Vivid'

  -- Font settings
  config.font = wezterm.font_with_fallback {
    'SauceCodePro Nerd Font',
    'ヒラギノ角ゴシック',
    'Apple Color Emoji',
  }
  config.font_size = 12.5
  config.line_height = 1.0

  -- Window appearance
  config.window_background_opacity = 0.85
  config.macos_window_background_blur = 5
  config.window_padding = { left = '0.5cell', right = '0.5cell', top = '0.5cell', bottom = '0.5cell' }

  -- Cursor settings
  config.default_cursor_style = 'BlinkingBar'

  -- Tab bar settings
  config.enable_tab_bar = false
end

return M