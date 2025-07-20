local wezterm = require "wezterm"

local M = {}

-- Helper function for toast notifications
local function toast(window, message)
  window:toast_notification('wezterm', message .. ' - ' .. os.date('%I:%M:%S %p'), nil, 4000)
end

function M.setup(config)
  -- Notification handling configuration
  -- https://wezterm.org/config/lua/config/notification_handling.html
  config.notification_handling = "AlwaysShow"

  -- System bell sound (for Claude Code task completion notifications)
  config.audible_bell = "SystemBeep"

  -- Event handlers for notifications
  wezterm.on('window-config-reloaded', function(window, pane)
    toast(window, 'Configuration reloaded!')
  end)
end

return M