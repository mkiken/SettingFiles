local wezterm = require "wezterm"
local config = wezterm.config_builder()
local action = wezterm.action

config.color_scheme = "Catppuccin Mocha"
-- config.color_scheme = 'iceberg'
config.font = wezterm.font_with_fallback {
  'SauceCodePro Nerd Font',
  'ヒラギノ角ゴシック',
  'Apple Color Emoji',
}
config.font_size = 12.5
config.line_height = 1.0
config.window_background_opacity = 0.85
config.macos_window_background_blur = 5

config.window_padding = { left = '0.5cell', right = '0.5cell', top = '0.5cell', bottom = '0.5cell' }
config.default_cursor_style = 'BlinkingBar'

config.enable_tab_bar = false

-- https://wezterm.org/config/lua/config/notification_handling.html
config.notification_handling = "SuppressFromFocusedTab"

return config
