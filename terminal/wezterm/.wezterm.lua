local wezterm = require "wezterm"
local config = wezterm.config_builder()

-- Get home directory and set the actual config directory path
local home = os.getenv("HOME") or os.getenv("USERPROFILE")
local config_dir = home .. "/Desktop/repository/SettingFiles/terminal/wezterm/"

-- Load modules from the same directory
package.path = config_dir .. "?.lua;" .. package.path

local appearance = require "appearance"
local keybinding = require "keybinding"
local notification = require "notification"
local other = require "other"

-- Apply configurations from each module
appearance.setup(config)
keybinding.setup(config)
notification.setup(config)
other.setup(config)

return config
