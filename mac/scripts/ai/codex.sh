#!/bin/zsh

source "${Repo}mac/scripts/ai/claude_mem.sh"
source "${Repo}mac/scripts/ai/rtk.sh"

function setup_codex_rtk() {
  echo "Ensuring Codex RTK command support..."

  require_rtk_token_killer
}

function setup_codex_caveman() {
  local caveman_skill="$HOME/.agents/skills/caveman/SKILL.md"

  echo "Ensuring Codex Caveman skill..."

  if [[ -f "$caveman_skill" ]]; then
    echo "✓ Codex Caveman skill already installed."
    return 0
  fi

  npx --yes skills@latest add JuliusBrussee/caveman --agent codex --global --skill caveman --yes || return 1

  if [[ ! -f "$caveman_skill" ]]; then
    echo "Error: Codex Caveman skill was not installed at $caveman_skill" >&2
    return 1
  fi
}

function update_codex_caveman() {
  local caveman_skill="$HOME/.agents/skills/caveman/SKILL.md"

  if [[ ! -f "$caveman_skill" ]]; then
    setup_codex_caveman
    return $?
  fi

  echo "Updating Codex Caveman skill..."
  npx --yes skills@latest update caveman --global --yes || return 1

  if [[ ! -f "$caveman_skill" ]]; then
    echo "Error: Codex Caveman skill disappeared after update: $caveman_skill" >&2
    return 1
  fi
}

function setup_codex_context_mode() {
  echo "Ensuring Codex context-mode plugin..."

  setup_context_mode_cli || return 1
  require_ai_setup_command codex || return 1
  require_ai_setup_command jq || return 1

  if ! codex plugin marketplace list | /usr/bin/grep -Fq "context-mode"; then
    codex plugin marketplace add mksglu/context-mode || return 1
  fi

  codex plugin marketplace upgrade context-mode >/dev/null 2>&1 || true

  if codex plugin list --json | jq -e '.installed[]? | select(.pluginId == "context-mode@context-mode" or (.name == "context-mode" and .marketplaceName == "context-mode"))' >/dev/null; then
    echo "✓ Codex context-mode plugin already installed."
  else
    codex plugin add context-mode@context-mode || return 1
  fi
}

function setup_codex_superpowers() {
  echo "Ensuring Codex Superpowers plugin..."

  require_ai_setup_command codex || return 1
  require_ai_setup_command jq || return 1

  if ! codex plugin marketplace list | /usr/bin/grep -Fq "openai-curated"; then
    codex plugin marketplace add openai/plugins || return 1
  fi

  # openai-curated may be a bundled local snapshot; refresh only when the CLI supports it.
  codex plugin marketplace upgrade openai-curated >/dev/null 2>&1 || true

  if codex plugin list --json | jq -e '.installed[]? | select(.pluginId == "superpowers@openai-curated" or (.name == "superpowers" and .marketplaceName == "openai-curated"))' >/dev/null; then
    echo "✓ Codex Superpowers plugin already installed."
  else
    codex plugin add superpowers@openai-curated || return 1
  fi
}

function setup_codex_claude_mem() {
  echo "Ensuring Codex claude-mem plugin..."

  require_ai_setup_command codex || return 1
  require_ai_setup_command jq || return 1

  # 既にインストール済みなら npx install を再実行しない。
  # claude-mem のインストーラーは再実行のたびに ~/.codex/config.toml に
  # [plugins.'claude-mem@...'] テーブルを追記するため、二重登録すると不正 TOML になる。
  if codex plugin list --json | jq -e '.installed[]? | select(.name == "claude-mem" or (.pluginId // "" | test("claude-mem")))' >/dev/null; then
    echo "✓ Codex claude-mem plugin already installed."
  else
    setup_claude_mem_for_ide codex-cli || return 1
  fi

  setup_claude_mem_runtime || return 1
}
