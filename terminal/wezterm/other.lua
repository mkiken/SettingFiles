local M = {}

function M.setup(config)
  -- Window close confirmation
  -- [Is it possible to quit wezterm without asking? · wezterm/wezterm · Discussion #5189](https://github.com/wezterm/wezterm/discussions/5189)
  config.window_close_confirmation = 'NeverPrompt'
end

return M