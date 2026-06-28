#!/bin/zsh

function setup_claude_context_mode() {
  echo "Ensuring Claude context-mode plugin..."

  setup_context_mode_cli || return 1
  require_ai_setup_command claude || return 1
  require_ai_setup_command jq || return 1

  if ! claude plugin marketplace list | /usr/bin/grep -Fq "context-mode"; then
    claude plugin marketplace add mksglu/context-mode || return 1
  fi

  claude plugin marketplace update context-mode || return 1

  if claude plugin list --json | jq -e '.[] | select(.id == "context-mode@context-mode")' >/dev/null; then
    claude plugin update context-mode@context-mode || return 1
  else
    claude plugin install context-mode@context-mode || return 1
  fi

  if ! claude plugin list --json | jq -e '.[] | select(.id == "context-mode@context-mode" and .enabled == true)' >/dev/null; then
    claude plugin enable context-mode@context-mode || return 1
  fi
}

function setup_claude_superpowers() {
  echo "Ensuring Claude Superpowers plugin..."

  require_ai_setup_command claude || return 1
  require_ai_setup_command jq || return 1

  if ! claude plugin marketplace list | /usr/bin/grep -Fq "claude-plugins-official"; then
    claude plugin marketplace add anthropics/claude-plugins-official || return 1
  fi

  claude plugin marketplace update claude-plugins-official || return 1

  if claude plugin list --json | jq -e '.[] | select(.id == "superpowers@claude-plugins-official")' >/dev/null; then
    claude plugin update superpowers@claude-plugins-official || return 1
  else
    claude plugin install superpowers@claude-plugins-official || return 1
  fi

  if ! claude plugin list --json | jq -e '.[] | select(.id == "superpowers@claude-plugins-official" and .enabled == true)' >/dev/null; then
    claude plugin enable superpowers@claude-plugins-official || return 1
  fi
}
