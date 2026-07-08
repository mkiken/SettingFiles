#!/bin/zsh

source "${Repo}mac/scripts/ai/claude_mem.sh"

function _remove_gemini_env_destination_symlink() {
  local dst="$1"

  if [[ -L "$dst" ]]; then
    echo "rm $dst"
    /bin/rm "$dst" || return 1
  fi
}

function sync_gemini_env_repo_to_home() {
  local src="${Repo}ai/gemini/.env"
  local dst="$HOME/.gemini/.env"

  echo "Syncing Gemini .env to home..."
  _remove_gemini_env_destination_symlink "$dst" || return 1
  smart_copy "$src" "$dst"
}

function sync_gemini_env_home_to_repo() {
  local src="$HOME/.gemini/.env"
  local dst="${Repo}ai/gemini/.env"

  if [[ ! -e "$src" && ! -L "$src" ]]; then
    echo "Skipping Gemini .env repo sync; source not found: $src"
    return 0
  fi

  echo "Syncing Gemini .env to repository..."
  _remove_gemini_env_destination_symlink "$dst" || return 1
  smart_copy "$src" "$dst"
}

function setup_gemini_context_mode() {
  echo "Ensuring Gemini context-mode CLI..."

  setup_context_mode_cli || return 1
  require_ai_setup_command jq || return 1

  smart_merge_json "${Repo}ai/gemini/settings.json" ~/.gemini/settings.json
}

function setup_gemini_superpowers() {
  echo "Ensuring Gemini Superpowers extension..."

  require_ai_setup_command gemini || return 1

  if gemini extensions list 2>&1 | /usr/bin/grep -Eq '^[^[:space:]]+[[:space:]]+superpowers[[:space:]]+\('; then
    gemini extensions update superpowers || return 1
  else
    gemini extensions install https://github.com/obra/superpowers --auto-update --consent || return 1
  fi

  gemini extensions enable superpowers || return 1
}

function setup_gemini_claude_mem() {
  echo "Ensuring Gemini claude-mem hooks..."

  require_ai_setup_command gemini || return 1

  setup_claude_mem_for_ide gemini-cli || return 1
  setup_claude_mem_runtime || return 1
}
