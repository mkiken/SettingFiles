local wezterm = require "wezterm"
local config = wezterm.config_builder()
local action = wezterm.action

config.color_scheme = 'iceberg'
config.font = wezterm.font_with_fallback {
  'SauceCodePro Nerd Font',
  'ヒラギノ角ゴシック',
  'Apple Color Emoji',
}
config.font_size = 12.0
config.line_height = 1.0
config.window_background_opacity = 0.85

config.window_padding = { left = '0.5cell', right = '0.5cell', top = '0.5cell', bottom = '0.5cell' }
config.default_cursor_style = 'BlinkingBar'

return config
