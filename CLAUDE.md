# CLAUDE.md

This file provides guidance to AI coding agents working in this repository. `AGENTS.md` at the repository root is a symlink to this file, so Codex reads the same content — keep instructions platform-neutral (no agent-specific plugin or skill references).

## Repository Overview

Personal dotfiles repository for managing development environment configurations across Mac and Windows. Uses symbolic links to synchronize settings.

## Repository Branch Policy

In this repository, implementation work may start directly on `main` or `master`.

If a workflow or skill requires explicit consent before starting implementation on `main` or `master`, treat this section as that standing consent for this repository.

This consent only covers starting implementation in place. Do not skip confirmation flows for destructive operations, commits, pushes, pull requests, deletes, deployments, external API writes, or any other side-effecting workflow that separately requires user confirmation.

## Key Commands

### Initial Setup
```bash
# Mac
cd mac && ./initialize

# Windows (PowerShell)
cd windows && ./initialize.ps1
```

### Update Environment
```bash
# Mac
cd mac && ./update

# Windows (PowerShell)
cd windows && ./update.ps1
```

### Homebrew Package Management
```bash
cd mac && brew bundle
```

### Regenerate AI Prompts

Canonical source-to-command mapping for regenerating committed outputs after editing prompt sources. The full init scripts (`mac/initialization/ai/{claude,gemini,codex}.sh`) cover everything; the targeted commands below are faster.

| Edited source | Regenerate with |
| --- | --- |
| `ai/common/prompt_base.md`, `ai/common/characters/*.md` (Claude/Gemini load these at runtime via `@file` — no regeneration needed) | Codex only: `mac/initialization/ai/codex.sh` (regenerates `_AGENTS.md`) |
| Shared-core skill sources (`ai/common/*_core.md`, `ai/{codex,gemini}/skills/*/skill_head.md`/`skill_tail.md`) | `zsh -c 'source mac/scripts/common.sh && generate_codex_skills && generate_gemini_skills'` |
| pr-review-subagents sources (`ai/common/pr_review_subagents/`, `ai/*/agents_src/`, codex `skill_head.md`/`skill_tail.md`) | `generate_pr_reviewer_agents <platform>` from `mac/scripts/common.sh` |

## Architecture

### Directory Structure
- `/ai/` - AI assistant configurations (Claude, Gemini, Serena)
- `/mac/` - macOS configurations, initialization, and update scripts
- `/windows/` - Windows configurations and scripts
- `/vimfiles/nvim/` - Neovim configuration (lazy.nvim)
- `/shell/zsh/` - Zsh configuration with znap plugin manager
- `/submodules/` - znap plugin manager (git submodule); other Zsh plugins are downloaded by znap at runtime
- `/gitfiles/` - Git configurations (gitui, lazygit, gh-dash, workmux)
- `/terminal/` - Terminal emulator configs (ghostty, etc.)

### Symlink Strategy
Initialize scripts create symbolic links from repository to system locations. The core utility functions are in `shell/zsh/alias/utils.zsh`:
- `make_symlink` - Idempotent symlink creation (skips if already correct)
- `smart_copy` - Diff-aware file copy with interactive overwrite prompt
- `smart_merge_json` - Deep-merge JSON files with conflict resolution (supports overwrite, keep, merge-with-priority)

Key symlinks:
- `ai/claude/_CLAUDE.md` → `~/.claude/CLAUDE.md`
- `ai/gemini/_GEMINI.md` → `~/.gemini/GEMINI.md`
- `ai/codex/_AGENTS.md` → `~/.codex/AGENTS.md`
- `~/.zshrc` loads `shell/zsh/managed.zsh` through a managed loader block
- `vimfiles/nvim` → `~/.config/nvim`
- `gitfiles/.gitconfig` → `~/.gitconfig`

Claude-specific files (agents, hooks, scripts) are individually symlinked into `~/.claude/`. Claude has no custom slash commands — former commands live as skills under `ai/claude/skills/`.

Skills (`ai/common/skills/`, `ai/{claude,gemini,codex}/skills/`) are symlinked per directory via `setup_ai_skills` (e.g. `~/.codex/skills/pr-review` → `ai/codex/skills/pr-review`), so edits to skill files take effect immediately — no rerun or regeneration needed (exception: generated `SKILL.md` files — all Codex shared-core skills and Gemini fact-based — must be regenerated from their sources; see "Regenerate AI Prompts" under Key Commands). The whole `ai/common` directory is also symlinked to `~/.gemini/common` and `~/.claude/common` for runtime file references.

`ai/claude/settings.json` is the exception: it is not symlinked. It is deep-merged into `~/.claude/settings.json` via `smart_merge_json`, and the two files diverge (the runtime file accumulates machine-local keys). Editing the repository source alone does not update the live file — apply changes with `mac/initialization/ai/claude.sh` / `mac/update`, or merge manually when immediate effect is needed.

### AI Configuration Generation
Both `_CLAUDE.md` and `_GEMINI.md` are static files using `@file` import syntax to compose prompts from shared source files at runtime:
- **Claude** (`ai/claude/_CLAUDE.md`): `@../common/prompt_base.md` + `@../common/characters/reimu.md`
- **Gemini** (`ai/gemini/_GEMINI.md`): `@../common/prompt_base.md` + `@../common/characters/rikka_takanashi.md` + inline Language rules

Edit the source files directly (`ai/common/prompt_base.md`, `ai/common/characters/*.md`) — no build step needed. Gemini additionally merges `ai/common/mcp.json` (and `mcp.local.json` if present) into its `settings.json`.

- **Codex** (`ai/codex/_AGENTS.md`): Codex's AGENTS.md does not support `@file` imports, so `mac/initialization/ai/codex.sh` (and `mac/updates/codex.sh`) generates `_AGENTS.md` by `cat`-concatenating `ai/common/prompt_base.md` + `ai/common/characters/nyaruko.md` + `ai/codex/codex_base.md`. The generated file is committed and symlinked to `~/.codex/AGENTS.md`. Edit the source files, never the generated `_AGENTS.md` (see "Regenerate AI Prompts" under Key Commands).

Shared-core skills follow one pattern: the skill body lives in core file(s) under `ai/common/`, loaded at runtime by Claude (`` !`/bin/cat ~/.claude/common/<core>.md` `` in the skill) and Gemini (`!{cat ~/.gemini/common/<core>.md}` in the command), and concatenated at build time by `generate_codex_skills` into the committed `ai/codex/skills/<name>/SKILL.md` (`skill_head.md` + core file(s) in listed order + `skill_tail.md` if present). When the Gemini adapter must stay a *skill* rather than a command (to keep keyword auto-activation), its `SKILL.md` is likewise generated at build time by `generate_gemini_skills` — Gemini skill files support no runtime inclusion (`!{...}` works only in commands). Edit the sources, never the generated `SKILL.md` files. Platform-specific bits (placeholders, confirmation primitive) live in each platform's adapter (Claude `SKILL.md` / Gemini `.toml` or `skill_head.md` / Codex `skill_head.md`).

| Skill | Core file(s) in `ai/common/` | Notes |
| --- | --- | --- |
| pr-review | `pr_review_core.md` + `pr_review_finding_format.md` | `pr_review_finding_format.md` defines the final output format (priority matrix, finding structure, section skeleton, 総合評価) shared with pr-review-subagents |
| pr-review-subagents | `pr_review_subagents/orchestrator_core.md` + `pr_review_finding_format.md` | reviewer agents are separately generated — see below |
| pr-comment-review | `pr_comment_review_core.md` | |
| pr-comment-implement | `pr_comment_implement_core.md` | |
| pr-comment-post | `pr_comment_post_core.md` | adapter-head bits: `ITEM_NUMBERS`, `{ai_header}`, confirmation primitive |
| pr-body | `pr_body_core.md` | |
| pr-create-by-branch | `pr_create_by_branch_core.md` | Claude and Codex only (no Gemini variant); adapter-head bits: `TARGET_BRANCH_ARG`, confirmation primitive |
| config-audit | `config_audit_core.md` | adapter-head bits: `PLATFORM_NAME`, `SCOPE`, `ENTRY_SCOPE`, `CONFIG_PATHS`, `GENERATED_ENTRY_FILE`, `SOURCE_FILES`, confirmation primitive |
| fact-based | `fact_based_core.md` | Gemini adapter is a generated skill (not a command); Claude adapter keeps `$ARGUMENTS` handling in head/tail around the runtime include |

Beyond its shared core (table above), the pr-review-subagents system has 21 reviewer subagent definitions (7 dimensions × 3 platforms) (`ai/claude/agents/pr-reviewer-*.md`, `ai/gemini/agents/pr-reviewer-*.md`, `ai/codex/agents/pr_reviewer_*.toml`) which are GENERATED and committed: `generate_pr_reviewer_agents` (`mac/scripts/common.sh`, called by the init/update scripts) assembles each from shared dimension fragments (`intro_<dim>.md`, `format_<dim>.md`) plus per-platform `ai/<platform>/agents_src/` files (`head_<dim>`, `rules_<dim>`, `rules_common`). Subagent definition files support no runtime file inclusion on any platform, hence build-time generation. Edit the sources, never the generated outputs.

### Claude Hooks
`ai/claude/hooks/` contains notification hooks symlinked into `~/.claude/hooks/`:
- `claude-hook.py` - Updates tmux window name to reflect Claude Code session status
- `stop-send-notification.sh` - Sends rich session notifications on completion

### Plugin Management

**Zsh (znap)**: Config in `shell/zsh/plugin.zsh`. Only znap itself is a git submodule (`submodules/zsh-snap`); all other Zsh plugins (fzf-tab, zsh-autosuggestions, F-Sy-H, etc.) are managed by znap at runtime. Plugins updated via `znap pull` in `mac/update`.

**Neovim (lazy.nvim)**: Plugins in `vimfiles/nvim/lua/plugins/`. VSCode Neovim uses separate `plugins_vscode/`. Updated via `nvim --headless "+Lazy! sync | TSUpdate" +qa` in `mac/update`.

## AI Prompt File Editing

When editing AI prompt files in this repository:

- **Default to English** for new content and modifications (reduces token consumption)
- **Exception**: If the original file uses a different language, follow that language (e.g., Japanese character dialogue examples)
- **Write concisely**: express new or modified prompt content as concisely as the meaning and intent allow — every loaded prompt consumes context. When condensing existing files, follow `ai/common/prompt_shortening_guide.md`.
- **Runtime loading differs per platform**: Claude Code and Gemini CLI load only the markdown body of agent/skill files as the prompt — frontmatter (including YAML `#` comments) costs zero runtime tokens. Codex instead injects the whole SKILL.md raw at invocation, frontmatter included, so for Codex skills every frontmatter line counts as prompt cost. Codex agent TOML files are parsed; `#` comments there cost nothing.
- **GENERATED-file notices** are placed where they cost no runtime tokens: YAML comments inside frontmatter for Claude/Gemini `pr-reviewer-*.md`, a `#` comment for Codex `pr_reviewer_*.toml`. Codex `SKILL.md` files intentionally carry no notice (raw injection would bill it) — the adjacent `skill_head.md` sources and this file are the edit guard. Do not add visible-body notices to generated files.

## Commit Message Convention

This repository enforces commitizen (czg) + commitlint via a `commit-msg` hook. Non-conforming commits are rejected immediately.

### Format

```
<type>(<scope>): <emoji> <subject>
```

Example: `perf(claude): ⚡ pr-review-subagentsスキルで止まりにくくする`

### Allowed Types and Scopes

The canonical source is `.commitlintrc.json`:
- Types: `rules.type-enum`
- Scopes: `rules.scope-enum`

Do not duplicate the allowed lists in this document. When changing commit types or scopes, update `.commitlintrc.json` first. Keep `.czrc` type prompts aligned only when type values change.

### Rules

- **scope is required** — empty scope will be rejected
- **subject**: 1–50 characters, must NOT start with an uppercase letter
- **emoji**: czg auto-prepends it; when committing manually (not via czg), include the appropriate emoji at the start of the subject
