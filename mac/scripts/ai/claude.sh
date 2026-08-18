#!/bin/zsh

source "${Repo}mac/scripts/ai/claude_mem.sh"
source "${Repo}mac/scripts/ai/rtk.sh"

function setup_claude_rtk() {
  echo "Ensuring Claude RTK hook..."

  require_rtk_token_killer || return 1
  ensure_rtk_hook "$HOME/.claude/settings.json" "PreToolUse" "Bash" "rtk hook claude"
}

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

function setup_claude_genshijin() {
  echo "Ensuring Claude genshijin plugin..."

  require_ai_setup_command claude || return 1
  require_ai_setup_command jq || return 1

  if ! claude plugin marketplace list | /usr/bin/grep -Fq "genshijin"; then
    claude plugin marketplace add InterfaceX-co-jp/genshijin || return 1
  fi

  claude plugin marketplace update genshijin || return 1

  if claude plugin list --json | jq -e '.[] | select(.id == "genshijin@genshijin")' >/dev/null; then
    claude plugin update genshijin@genshijin || return 1
  else
    claude plugin install genshijin@genshijin || return 1
  fi

  if ! claude plugin list --json | jq -e '.[] | select(.id == "genshijin@genshijin" and .enabled == true)' >/dev/null; then
    claude plugin enable genshijin@genshijin || return 1
  fi
}

function setup_claude_dig() {
  echo "Ensuring Claude dig plugin..."

  require_ai_setup_command claude || return 1
  require_ai_setup_command jq || return 1

  # marketplace名(kuu-marketplace)とrepo名(fumiya-kume/claude-code)が不一致。
  # addはrepo指定、以後のupdate/参照はmarketplace名で行う。
  if ! claude plugin marketplace list | /usr/bin/grep -Fq "kuu-marketplace"; then
    claude plugin marketplace add fumiya-kume/claude-code || return 1
  fi

  claude plugin marketplace update kuu-marketplace || return 1

  if claude plugin list --json | jq -e '.[] | select(.id == "dig@kuu-marketplace")' >/dev/null; then
    claude plugin update dig@kuu-marketplace || return 1
  else
    claude plugin install dig@kuu-marketplace || return 1
  fi

  if ! claude plugin list --json | jq -e '.[] | select(.id == "dig@kuu-marketplace" and .enabled == true)' >/dev/null; then
    claude plugin enable dig@kuu-marketplace || return 1
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

function setup_claude_example_skills() {
  echo "Ensuring Claude example-skills plugin (skill-creator)..."

  require_ai_setup_command claude || return 1
  require_ai_setup_command jq || return 1

  if ! claude plugin marketplace list | /usr/bin/grep -Fq "anthropic-agent-skills"; then
    claude plugin marketplace add anthropics/skills || return 1
  fi

  claude plugin marketplace update anthropic-agent-skills || return 1

  if claude plugin list --json | jq -e '.[] | select(.id == "example-skills@anthropic-agent-skills")' >/dev/null; then
    claude plugin update example-skills@anthropic-agent-skills || return 1
  else
    claude plugin install example-skills@anthropic-agent-skills || return 1
  fi

  if ! claude plugin list --json | jq -e '.[] | select(.id == "example-skills@anthropic-agent-skills" and .enabled == true)' >/dev/null; then
    claude plugin enable example-skills@anthropic-agent-skills || return 1
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
