local wezterm = require "wezterm"

local M = {}

function M.setup(config)
  -- Key bindings
  config.keys = {
    -- Alt+Enter for Claude Code newline
    {
      key = 'Enter',
      mods = 'ALT',
      action = wezterm.action.SendString('\n')
    },
    -- Shift+Enter for newline
    {
      key = 'Enter',
      mods = 'SHIFT',
      action = wezterm.action.SendString('\n')
    },
    -- Cmd+Enter for fullscreen toggle
    {
      key = 'Enter',
      mods = 'SUPER',
      action = wezterm.action.ToggleFullScreen,
    },
    -- Disable Ctrl+h default assignment
    {
      key = 'h',
      mods = 'CTRL',
      action = wezterm.action.DisableDefaultAssignment,
    },
  }
end

return M