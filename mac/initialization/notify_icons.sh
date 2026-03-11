#!/bin/zsh

source "$(dirname "$0")/../scripts/common.sh"

# Create notify-icons directory
mkdir -p ~/.config/notify-icons

# App list: bundle_id, app_name, icns_filename
local -A app_icons
app_icons=(
  "com.mitchellh.ghostty"   "Ghostty.app/Contents/Resources/Ghostty.icns"
  "com.microsoft.VSCode"    "Visual Studio Code.app/Contents/Resources/Code.icns"
  "com.jetbrains.goland"    "GoLand.app/Contents/Resources/goland.icns"
)

for bundle_id icns_path in "${(@kv)app_icons}"; do
  local full_icns="/Applications/${icns_path}"
  if [[ ! -f "$full_icns" ]]; then
    full_icns="${HOME}/Applications/${icns_path}"
  fi
  local output="${HOME}/.config/notify-icons/${bundle_id}.png"

  # Skip if app is not installed
  if [[ ! -f "$full_icns" ]]; then
    echo "  Skipping ${bundle_id} (app not found)"
    continue
  fi

  # Skip if icon already exists
  if [[ -f "$output" ]]; then
    echo "  Skipping ${bundle_id} (icon already exists)"
    continue
  fi

  sips -s format png "$full_icns" --out "$output" >/dev/null 2>&1
  echo "  Created: ${bundle_id}.png"
done

echo 'Notify icons configured.'
