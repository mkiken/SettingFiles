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
config.notification_handling = "AlwaysShow"

-- システムベル音を有効化（Claude Codeのタスク完了通知用）
config.audible_bell = "SystemBeep"

-- Alt+Enter for Claude Code newline
config.keys = {
  {
    key = 'Enter',
    mods = 'ALT',
    action = wezterm.action.SendString('\n')
  },
  {
    key = 'Enter',
    mods = 'SHIFT',
    action = wezterm.action.SendString('\n')
  },
}

-- Notification when the configuration is reloaded
local function toast(window, message)
 window:toast_notification('wezterm', message .. ' - ' .. os.date('%I:%M:%S %p'), nil, 1000)
end

wezterm.on('window-config-reloaded', function(window, pane)
 toast(window, 'Configuration reloaded!')
end)

return config
