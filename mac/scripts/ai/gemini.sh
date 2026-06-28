#!/bin/zsh

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
