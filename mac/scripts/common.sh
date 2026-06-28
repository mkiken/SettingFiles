#!/bin/zsh

# 関数定義を読み込み
source "$(dirname "$(dirname "$(dirname "$(realpath "${(%):-%x}")")")")/shell/zsh/alias/utils.zsh"

# set Repo "$HOME/Desktop/repository/SettingFiles/"
Repo="$(dirname "$(dirname "$(dirname "$(realpath "${(%):-%x}")")")")/"
Repo_shell="${Repo}shell/"

function untap_stale_homebrew_taps() {
  local stale_taps=(
    "aku11i/tap"
    "dwarvesf/tap"
    "dwarvesf/homebrew-tap"
  )

  local stale_tap
  for stale_tap in "${stale_taps[@]}"; do
    if HOMEBREW_NO_AUTO_UPDATE=1 brew tap | /usr/bin/grep -Fxq "$stale_tap"; then
      HOMEBREW_NO_AUTO_UPDATE=1 brew untap "$stale_tap"
    fi
  done
}

function setup_ai_skills() {
  local dest_dir="$1"
  shift

  mkdir -p "$dest_dir"

  local skills_root skill_dir skill_name
  for skills_root in "$@"; do
    if [[ ! -d "$skills_root" ]]; then
      continue
    fi

    for skill_dir in "${skills_root}"/*(/N); do
      skill_name=$(basename "$skill_dir")
      make_symlink "$skill_dir" "${dest_dir}/${skill_name}"
    done
  done
}

function setup_ai_pr_tools() {
  local source_dir="${Repo}shell/common/pr"
  local dest_bin="$HOME/.config/ai-pr/bin"
  local file

  if [[ -d "$dest_bin" && ! -L "$dest_bin" ]]; then
    for file in "${source_dir}"/*.sh; do
      if [[ -f "$file" ]]; then
        make_symlink "$file" "${dest_bin}/$(basename "$file")"
      fi
    done
    return
  fi

  make_symlink "$source_dir" "$dest_bin"
}

function require_ai_setup_command() {
  local command_name="$1"

  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Error: $command_name is not installed or not on PATH." >&2
    return 1
  fi
}

function require_context_mode_node() {
  require_ai_setup_command node || return 1
  require_ai_setup_command npm || return 1

  node -e '
const [major, minor] = process.versions.node.split(".").map(Number);
if (major < 22 || (major === 22 && minor < 5)) {
  console.error(`Error: context-mode requires Node.js >= 22.5.0. Found ${process.versions.node}.`);
  process.exit(1);
}
'
}

function setup_context_mode_cli() {
  if [[ "${CONTEXT_MODE_CLI_SETUP_DONE:-}" == "1" ]]; then
    echo "✓ context-mode CLI already handled for this run."
    return 0
  fi

  echo "Ensuring context-mode CLI..."

  require_context_mode_node || return 1

  npm install -g context-mode@latest || return 1

  export CONTEXT_MODE_CLI_SETUP_DONE=1
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

function setup_gemini_context_mode() {
  echo "Ensuring Gemini context-mode CLI..."

  setup_context_mode_cli || return 1
  require_ai_setup_command jq || return 1

  smart_merge_json "${Repo}ai/gemini/settings.json" ~/.gemini/settings.json
}

function setup_codex_context_mode() {
  echo "Ensuring Codex context-mode plugin..."

  setup_context_mode_cli || return 1
  require_ai_setup_command codex || return 1
  require_ai_setup_command jq || return 1

  smart_merge_toml "${Repo}ai/codex/config.toml" ~/.codex/config.toml || return 1

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
