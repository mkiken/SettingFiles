#!/bin/zsh

function setup_claude_mem_for_ide() {
  local ide_id="$1"

  if [[ -z "$ide_id" ]]; then
    echo "Usage: setup_claude_mem_for_ide <ide-id>" >&2
    return 1
  fi

  require_ai_setup_command node || return 1
  require_ai_setup_command npm || return 1
  require_ai_setup_command uv || return 1
  require_ai_setup_command bun || return 1

  local provider="${CLAUDE_MEM_PROVIDER:-claude}"

  if [[ "$provider" == "claude" ]]; then
    npx --yes claude-mem@latest install \
      --ide "$ide_id" \
      --provider "${CLAUDE_MEM_PROVIDER:-claude}" \
      --model "${CLAUDE_MEM_MODEL:-claude-haiku-4-5-20251001}" \
      --runtime "${CLAUDE_MEM_RUNTIME:-worker}" < /dev/null || return 1
  else
    npx --yes claude-mem@latest install \
      --ide "$ide_id" \
      --provider "${CLAUDE_MEM_PROVIDER:-claude}" \
      --runtime "${CLAUDE_MEM_RUNTIME:-worker}" < /dev/null || return 1
  fi
}

function setup_claude_mem_runtime() {
  local runtime="${CLAUDE_MEM_RUNTIME:-worker}"

  npx --yes claude-mem@latest repair || return 1

  if [[ "$runtime" == "worker" ]]; then
    if npx --yes claude-mem@latest status 2>/dev/null | /usr/bin/grep -Fq "Worker is running"; then
      echo "✓ claude-mem worker already running."
    else
      npx --yes claude-mem@latest start || return 1
    fi
  else
    echo "Skipping claude-mem worker start for runtime: $runtime"
  fi
}
