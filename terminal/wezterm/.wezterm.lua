local wezterm = require "wezterm"
local config = wezterm.config_builder()

-- Get the actual directory of this config file
-- Use wezterm's executable path to find the real config location
local handle = io.popen("readlink -f " .. wezterm.config_file .. " 2>/dev/null || echo " .. wezterm.config_file)
local real_config_path = handle:read("*a"):gsub("\n", "")
handle:close()

local config_dir = real_config_path:match("(.*/)")

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
