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

function setup_claude_mem() {
  echo "Ensuring Claude claude-mem plugin..."

  require_ai_setup_command claude || return 1
  require_ai_setup_command jq || return 1
  require_ai_setup_command node || return 1
  require_ai_setup_command npm || return 1
  require_ai_setup_command uv || return 1
  require_ai_setup_command bun || return 1

  local provider="${CLAUDE_MEM_PROVIDER:-claude}"
  local runtime="${CLAUDE_MEM_RUNTIME:-worker}"

  if [[ "$provider" == "claude" ]]; then
    npx --yes claude-mem@latest install \
      --ide claude-code \
      --provider "${CLAUDE_MEM_PROVIDER:-claude}" \
      --model "${CLAUDE_MEM_MODEL:-claude-haiku-4-5-20251001}" \
      --runtime "${CLAUDE_MEM_RUNTIME:-worker}" || return 1
  else
    npx --yes claude-mem@latest install \
      --ide claude-code \
      --provider "${CLAUDE_MEM_PROVIDER:-claude}" \
      --runtime "${CLAUDE_MEM_RUNTIME:-worker}" || return 1
  fi

  npx --yes claude-mem@latest repair || return 1
  claude plugin marketplace update thedotmack || return 1

  if [[ "$runtime" == "worker" ]]; then
    if npx --yes claude-mem@latest status 2>/dev/null | /usr/bin/grep -Fq "Worker is running"; then
      echo "✓ claude-mem worker already running."
    else
      npx --yes claude-mem@latest start || return 1
    fi
  else
    echo "Skipping claude-mem worker start for runtime: $runtime"
  fi

  if ! claude plugin list --json | jq -e '.[] | select(.id == "claude-mem@thedotmack" and .enabled == true)' >/dev/null; then
    claude plugin enable claude-mem@thedotmack || return 1
  fi
}
