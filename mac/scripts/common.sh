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

# pr-review-subagents のレビュアー定義を共有フラグメントから生成する
# 生成物: ai/claude/agents/pr-reviewer-*.md, ai/gemini/agents/pr-reviewer-*.md, ai/codex/agents/pr_reviewer_*.toml
# 編集は ai/common/pr_review_subagents/ と ai/<platform>/agents_src/ へ（生成物は編集しない）
function generate_pr_reviewer_agents() {
  local platform="$1"
  local common="${Repo}ai/common/pr_review_subagents"
  local src="${Repo}ai/${platform}/agents_src"
  local notice="GENERATED FILE - do not edit. Built by generate_pr_reviewer_agents (mac/scripts/common.sh) from ai/common/pr_review_subagents/ and ai/${platform}/agents_src/. Edit those sources, then rerun mac/updates/${platform}.sh."
  local dim out

  for dim in bugs security architecture errors history tests; do
    case "$platform" in
      claude | gemini)
        out="${Repo}ai/${platform}/agents/pr-reviewer-${dim}.md"
        {
          /bin/cat "${src}/head_${dim}.md"
          printf '<!-- %s -->\n' "$notice"
          echo
          /bin/cat "${common}/intro_${dim}.md"
          echo
          /bin/cat "${src}/rules_${dim}.md"
          /bin/cat "${src}/rules_common.md"
          echo
          if [[ "$platform" == "gemini" ]]; then
            # Gemini のみ、指摘テンプレートのヘッダー行直後に行番号根拠の行を挿入する
            awk '{print} /\(信頼度: XX\)$/{print "- **行番号根拠**: FILE path/to/file.ext / NEW 42 exact snippet from the line-numbered diff"}' "${common}/format_${dim}.md"
          else
            /bin/cat "${common}/format_${dim}.md"
          fi
        } > "$out"
        ;;
      codex)
        out="${Repo}ai/codex/agents/pr_reviewer_${dim}.toml"
        # 本文は TOML の ''' リテラル文字列に埋め込むため、フラグメントに ''' が混入したら生成を失敗させる
        if /usr/bin/grep -q "'''" "${common}/intro_${dim}.md" "${common}/format_${dim}.md" "${src}/rules_${dim}.md" "${src}/rules_common.md"; then
          echo "Error: ''' found in pr_reviewer_${dim} fragments; it would break the TOML literal string." >&2
          return 1
        fi
        {
          printf '# %s\n' "$notice"
          /bin/cat "${src}/head_${dim}.toml"
          /bin/cat "${common}/intro_${dim}.md"
          echo
          /bin/cat "${src}/rules_${dim}.md"
          /bin/cat "${src}/rules_common.md"
          echo
          /bin/cat "${common}/format_${dim}.md"
          printf "'''\n"
        } > "$out"
        ;;
      *)
        echo "Error: unknown platform '${platform}' for generate_pr_reviewer_agents." >&2
        return 1
        ;;
    esac
  done
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
