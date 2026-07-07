# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Personal dotfiles repository for managing development environment configurations across Mac and Windows. Uses symbolic links to synchronize settings.

## Repository Branch Policy

In this repository, implementation work may start directly on `main` or `master`.

If a workflow or skill such as `superpowers:executing-plans` requires explicit consent before starting implementation on `main` or `master`, treat this section as that standing consent for this repository.

This consent only covers starting implementation in place. Do not skip confirmation flows for destructive operations, commits, pushes, pull requests, deletes, deployments, external API writes, or any other side-effecting workflow that separately requires user confirmation.

## Key Commands

### Initial Setup
```bash
# Mac (8-step setup: copy_files → homebrew → dev_tools → tmux → notify_icons → git_setup → system_setup → AI assistants)
cd mac && ./initialize

# Windows (PowerShell)
cd windows && ./initialize.ps1
```

### Update Environment
```bash
# Mac: submodules → brew → npm → pipx → AI tools → nvim plugins → znap → gh extensions → zcompile
cd mac && ./update

# Windows (PowerShell)
cd windows && ./update.ps1
```

### Homebrew Package Management
```bash
cd mac && brew bundle
```

### Regenerate AI Prompts
```bash
# After editing source files in ai/common/ or ai/claude/ or ai/gemini/ or ai/codex/
mac/initialization/ai/claude.sh
mac/initialization/ai/gemini.sh
mac/initialization/ai/codex.sh
```

After editing pr-review-subagents sources (`ai/common/pr_review_subagents/`, `ai/*/agents_src/`, codex `skill_head.md`/`skill_tail.md`), regenerate the committed outputs with the scripts above, or run `generate_pr_reviewer_agents <platform>` from `mac/scripts/common.sh` directly.

After editing shared-core skill sources (`ai/common/*_core.md`, `ai/codex/skills/*/skill_head.md`/`skill_tail.md`), regenerate the committed Codex `SKILL.md` files with `generate_codex_skills` from `mac/scripts/common.sh` (zsh: `zsh -c 'source mac/scripts/common.sh && generate_codex_skills'`) — no need to run the full init/update scripts.

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

Skills (`ai/common/skills/`, `ai/{claude,gemini,codex}/skills/`) are symlinked per directory via `setup_ai_skills` (e.g. `~/.codex/skills/pr-review` → `ai/codex/skills/pr-review`), so edits to skill files take effect immediately — no rerun or regeneration needed (exception: generated Codex `SKILL.md` files such as pr-review and pr-review-subagents must be regenerated from their sources). The whole `ai/common` directory is also symlinked to `~/.gemini/common` and `~/.claude/common` for runtime file references.

`ai/claude/settings.json` is the exception: it is not symlinked. It is deep-merged into `~/.claude/settings.json` via `smart_merge_json`, and the two files diverge (the runtime file accumulates machine-local keys). Editing the repository source alone does not update the live file — apply changes with `mac/initialization/ai/claude.sh` / `mac/update`, or merge manually when immediate effect is needed.

### AI Configuration Generation
Both `_CLAUDE.md` and `_GEMINI.md` are static files using `@file` import syntax to compose prompts from shared source files at runtime:
- **Claude** (`ai/claude/_CLAUDE.md`): `@../common/prompt_base.md` + `@../common/characters/reimu.md`
- **Gemini** (`ai/gemini/_GEMINI.md`): `@../common/prompt_base.md` + `@../common/characters/rikka_takanashi.md` + inline Language rules

Edit the source files directly (`ai/common/prompt_base.md`, `ai/common/characters/*.md`) — no build step needed. Gemini additionally merges `ai/common/mcp.json` (and `mcp.local.json` if present) into its `settings.json`.

- **Codex** (`ai/codex/_AGENTS.md`): Codex's AGENTS.md does not support `@file` imports, so `mac/initialization/ai/codex.sh` (and `mac/updates/codex.sh`) generates `_AGENTS.md` by `cat`-concatenating `ai/common/prompt_base.md` + `ai/common/characters/nyaruko.md` + `ai/codex/codex_base.md`. The generated file is committed and symlinked to `~/.codex/AGENTS.md`. Edit the source files (not the generated `_AGENTS.md`); regenerate with `mac/initialization/ai/codex.sh`.

The pr-review shared body lives in `ai/common/pr_review_core.md` and is loaded at runtime by Claude (`` !`/bin/cat ~/.claude/common/pr_review_core.md` `` in the skill) and Gemini (`!{cat ~/.gemini/common/pr_review_core.md}`). For Codex, the same scripts generate `ai/codex/skills/pr-review/SKILL.md` from `skill_head.md` + `pr_review_core.md` + `skill_tail.md`; edit those sources, not the generated `SKILL.md`. The pr-comment-review shared body follows the same pattern: `ai/common/pr_comment_review_core.md` is loaded at runtime by Claude/Gemini, and the same scripts generate `ai/codex/skills/pr-comment-review/SKILL.md` from `skill_head.md` + `pr_comment_review_core.md`. The pr-comment-implement shared body follows it too: `ai/common/pr_comment_implement_core.md` is loaded at runtime by Claude/Gemini, and the same scripts generate `ai/codex/skills/pr-comment-implement/SKILL.md` from `skill_head.md` + `pr_comment_implement_core.md`. The pr-comment-post shared body follows it as well: `ai/common/pr_comment_post_core.md` is loaded at runtime by Claude/Gemini, and the same scripts generate `ai/codex/skills/pr-comment-post/SKILL.md` from `skill_head.md` + `pr_comment_post_core.md` (platform-specific bits — `ITEM_NUMBERS`, `{ai_header}`, confirmation primitive — are defined in each platform's adapter head). The pr-create-by-branch shared body follows the same pattern for Claude and Codex only (no Gemini variant): `ai/common/pr_create_by_branch_core.md` is loaded at runtime by Claude, and the same scripts generate `ai/codex/skills/pr-create-by-branch/SKILL.md` from `skill_head.md` + `pr_create_by_branch_core.md` (platform-specific bits — `TARGET_BRANCH_ARG`, confirmation primitive — live in each adapter head).

The pr-review-subagents system is centralized in `ai/common/pr_review_subagents/`: `orchestrator_core.md` (Aggregate + Final Format) is loaded at runtime by Claude (`` !`/bin/cat ~/.claude/common/pr_review_subagents/orchestrator_core.md` `` in the skill) and Gemini (`!{cat ~/.gemini/common/pr_review_subagents/orchestrator_core.md}` in the command), and concatenated at build time into `ai/codex/skills/pr-review-subagents/SKILL.md` (from `skill_head.md` + `orchestrator_core.md` + `skill_tail.md`). The 18 reviewer subagent definitions (`ai/claude/agents/pr-reviewer-*.md`, `ai/gemini/agents/pr-reviewer-*.md`, `ai/codex/agents/pr_reviewer_*.toml`) are GENERATED and committed: `generate_pr_reviewer_agents` (`mac/scripts/common.sh`, called by the init/update scripts) assembles each from shared dimension fragments (`intro_<dim>.md`, `format_<dim>.md`) plus per-platform `ai/<platform>/agents_src/` files (`head_<dim>`, `rules_<dim>`, `rules_common`). Subagent definition files support no runtime file inclusion on any platform, hence build-time generation. Edit the sources, never the generated outputs.

### Claude Hooks
`ai/claude/hooks/` contains notification hooks symlinked into `~/.claude/hooks/`:
- `claude-hook.py` - Updates tmux window name to reflect Claude Code session status
- `stop-send-notification.sh` - Sends rich session notifications on completion (transcript analysis, duration, task type inference)

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
