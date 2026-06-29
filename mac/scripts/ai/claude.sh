#!/bin/zsh

source "${Repo}mac/scripts/ai/claude_mem.sh"

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

function setup_claude_mem() {
  echo "Ensuring Claude claude-mem plugin..."

  require_ai_setup_command claude || return 1
  require_ai_setup_command jq || return 1

  setup_claude_mem_for_ide claude-code || return 1
  setup_claude_mem_runtime || return 1
  claude plugin marketplace update thedotmack || return 1

  if ! claude plugin list --json | jq -e '.[] | select(.id == "claude-mem@thedotmack" and .enabled == true)' >/dev/null; then
    claude plugin enable claude-mem@thedotmack || return 1
  fi
}
