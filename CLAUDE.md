# CLAUDE.md

Guidance for AI coding agents working in this repository. Root `AGENTS.md` is a symlink to this file (Codex reads the same content) — keep instructions platform-neutral (no agent-specific plugin or skill references).

## Repository Overview

Personal dotfiles for Mac and Windows development environments, synchronized via symbolic links.

## Repository Branch Policy

Implementation work may start directly on `main`/`master`; when a workflow or skill requires explicit consent for that, treat this section as standing consent. It covers only starting implementation in place — never skip separately required confirmation flows for destructive or side-effecting operations (commits, pushes, pull requests, deletes, deployments, external API writes).

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

Canonical source-to-command mapping for regenerating committed outputs. The full init scripts (`mac/initialization/ai/{claude,gemini,codex}.sh`) cover everything; the targeted commands below are faster.

| Edited source | Regenerate with |
| --- | --- |
| `ai/common/prompt_base.md`, `ai/common/characters/*.md` (Claude/Gemini load these at runtime via `@file`) | Codex only: `mac/initialization/ai/codex.sh` (regenerates `_AGENTS.md`) |
| Shared-core skill sources (`ai/common/*_core.md`, `ai/{codex,gemini}/skills/*/skill_head.md`/`skill_tail.md`) | `zsh -c 'source mac/scripts/common.sh && generate_codex_skills && generate_gemini_skills'` |
| pr-review-subagents sources (`ai/common/pr_review_subagents/`, `ai/*/agents_src/`, codex `skill_head.md`/`skill_tail.md`) | `generate_pr_reviewer_agents <platform>` from `mac/scripts/common.sh` |
| config-audit auditor sources (`ai/common/config_audit_subagents/`, `ai/*/agents_src/config_audit/`) | `generate_config_auditor_agents <platform>` from `mac/scripts/common.sh` |

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
Initialize scripts symlink repository files to system locations; core utility functions live in `shell/zsh/alias/utils.zsh`:
- `make_symlink` - Idempotent symlink creation (skips if already correct)
- `smart_copy` - Diff-aware file copy with interactive overwrite prompt
- `smart_merge_json` - Deep-merge JSON files with conflict resolution (supports overwrite, keep, merge-with-priority)

When editing shell helpers, do not use global variables for temporary return values or cross-call state. Prefer stdout, explicit arguments, or safe assignment into caller-owned `local` variables so parallel shells and nested calls cannot observe stale state.

Key symlinks:
- `ai/claude/_CLAUDE.md` → `~/.claude/CLAUDE.md`
- `ai/gemini/_GEMINI.md` → `~/.gemini/GEMINI.md`
- `ai/codex/_AGENTS.md` → `~/.codex/AGENTS.md`
- `~/.zshrc` loads `shell/zsh/managed.zsh` through a managed loader block
- `vimfiles/nvim` → `~/.config/nvim`
- `gitfiles/.gitconfig` → `~/.gitconfig`

Claude-specific files (agents, hooks, scripts) are individually symlinked into `~/.claude/`. Claude has no custom slash commands — former commands live as skills under `ai/claude/skills/`.

Skills (`ai/common/skills/`, `ai/{claude,gemini,codex}/skills/`) are symlinked per directory into `~/.<platform>/skills/` via `setup_ai_skills`, so skill edits take effect immediately — except generated `SKILL.md` files (all Codex shared-core skills and Gemini fact-based), which must be regenerated from their sources (see "Regenerate AI Prompts" under Key Commands). The whole `ai/common` directory is also symlinked to `~/.gemini/common` and `~/.claude/common` for runtime file references.

`ai/claude/settings.json` is the exception: not symlinked but deep-merged into `~/.claude/settings.json` via `smart_merge_json`, and the two files diverge (the live file accumulates machine-local keys). Editing the repository source alone does not update the live file — apply with `mac/initialization/ai/claude.sh` / `mac/update`, or merge manually for immediate effect.

### AI Configuration Generation
Throughout this section: edit the sources, never the generated committed outputs — regenerate via the "Regenerate AI Prompts" table under Key Commands.

Both `_CLAUDE.md` and `_GEMINI.md` are static files using `@file` import syntax to compose prompts from shared source files at runtime:
- **Claude** (`ai/claude/_CLAUDE.md`): `@../common/prompt_base.md` + `@../common/characters/reimu.md`
- **Gemini** (`ai/gemini/_GEMINI.md`): `@../common/prompt_base.md` + `@../common/characters/rikka_takanashi.md` + inline Language rules

Edit these sources directly — no build step. Gemini additionally merges `ai/common/mcp.json` (and `mcp.local.json` if present) into its `settings.json`.

- **Codex** (`ai/codex/_AGENTS.md`): Codex's AGENTS.md does not support `@file` imports, so `mac/initialization/ai/codex.sh` (and `mac/updates/codex.sh`) generates `_AGENTS.md` by `cat`-concatenating `ai/common/prompt_base.md` + `ai/common/characters/nyaruko.md` + `ai/codex/codex_base.md`; the generated file is committed and symlinked to `~/.codex/AGENTS.md`.

Shared-core skills follow one pattern: the skill body lives in core file(s) under `ai/common/`, loaded at runtime by Claude (`` !`/bin/cat ~/.claude/common/<core>.md` `` in the skill) and Gemini (`!{cat ~/.gemini/common/<core>.md}` in the command), and concatenated at build time by `generate_codex_skills` into the committed `ai/codex/skills/<name>/SKILL.md` (`skill_head.md` + core file(s) in listed order + `skill_tail.md` if present). When a Gemini adapter must stay a *skill* rather than a command (for keyword auto-activation), its `SKILL.md` is likewise build-time generated by `generate_gemini_skills` — Gemini skill files support no runtime inclusion (`!{...}` works only in commands). Platform-specific bits (placeholders, confirmation primitive) live in each platform's adapter (Claude `SKILL.md` / Gemini `.toml` or `skill_head.md` / Codex `skill_head.md`).

| Skill | Core file(s) in `ai/common/` | Notes |
| --- | --- | --- |
| pr-review | `pr_review_core.md` + `pr_review_finding_format.md` | `pr_review_finding_format.md` defines the shared final output format (priority matrix, finding structure, section skeleton, 総合評価) |
| pr-review-subagents | `pr_review_subagents/orchestrator_core.md` + `pr_review_finding_format.md` | reviewer agents are separately generated — see below |
| pr-comment-review | `pr_comment_review_core.md` | |
| pr-comment-implement | `pr_comment_implement_core.md` | |
| pr-comment-post | `pr_comment_post_core.md` | adapter-head bits: `ITEM_NUMBERS`, `{ai_header}`, confirmation primitive |
| pr-body | `pr_body_core.md` + `pr_body_format.md` | `pr_body_format.md` defines the shared PR body format (section skeleton, drafting rules) — also used by pr-create-by-branch |
| pr-create-by-branch | `pr_create_by_branch_core.md` + `pr_body_format.md` | Claude and Codex only (no Gemini variant); adapter-head bits: `TITLE_ARG`, `TARGET_BRANCH_ARG`, confirmation primitive |
| config-audit | `config_audit_subagents/orchestrator_core.md` | auditor agents are separately generated — see below; adapter-head bits: `PLATFORM_NAME`, `SCOPE`, `ENTRY_SCOPE`, `CONFIG_PATHS`, `GENERATED_ENTRY_FILE`, `SOURCE_FILES`, confirmation primitive |
| fact-based | `fact_based_core.md` | Gemini adapter is a generated skill (not a command); Claude adapter keeps `$ARGUMENTS` handling in head/tail around the runtime include |

When changing a skill's core composition or adapter-head bits, update this table in the same commit.

Beyond their shared cores (table above), two skill families have GENERATED, committed subagent definitions, assembled by functions in `mac/scripts/common.sh` (called by the init/update scripts). Subagent definition files support no runtime file inclusion on any platform, hence build-time generation.

- **pr-review-subagents** — 21 reviewer agents (7 dimensions × 3 platforms: `ai/claude/agents/pr-reviewer-*.md`, `ai/gemini/agents/pr-reviewer-*.md`, `ai/codex/agents/pr_reviewer_*.toml`): `generate_pr_reviewer_agents` assembles each from shared dimension fragments (`intro_<dim>.md`, `format_<dim>.md`) plus per-platform `ai/<platform>/agents_src/` files (`head_<dim>`, `rules_<dim>`, `rules_common`).
- **config-audit** — 18 auditor agents (6 dimensions × 3 platforms: `config-auditor-*.md` / `config_auditor_*.toml` in the same `agents` dirs): `generate_config_auditor_agents` assembles each from `ai/common/config_audit_subagents/` fragments (`intro_<dim>.md`, shared `rules_common.md`, `format_<dim>.md`) plus per-platform `ai/<platform>/agents_src/config_audit/head_<dim>` files.

### Claude Hooks
`ai/claude/hooks/` contains notification hooks symlinked into `~/.claude/hooks/`:
- `claude-hook.py` - Updates tmux window name to reflect Claude Code session status
- `stop-send-notification.sh` - Sends rich session notifications on completion

### Plugin Management

**Zsh (znap)**: Config in `shell/zsh/plugin.zsh`. Plugins updated via `znap pull` in `mac/update` (submodule/runtime split: see Directory Structure).

**Neovim (lazy.nvim)**: Plugins in `vimfiles/nvim/lua/plugins/`. VSCode Neovim uses separate `plugins_vscode/`. Updated via `nvim --headless "+Lazy! sync | TSUpdate" +qa` in `mac/update`.

## AI Prompt File Editing

When editing AI prompt files in this repository:

- **Default to English** for new or modified content (reduces token consumption); if the original file uses a different language, follow it (e.g. Japanese character dialogue examples)
- **Write concisely**: as concise as meaning and intent allow — every loaded prompt consumes context. When condensing existing files, follow `ai/common/prompt_shortening_guide.md`.
- **Runtime loading differs per platform**: Claude Code and Gemini CLI load only the markdown body of agent/skill files as the prompt — frontmatter (including YAML `#` comments) costs zero runtime tokens. Codex instead injects the whole SKILL.md raw at invocation, so every Codex skill frontmatter line counts as prompt cost. Codex agent TOML files are parsed; `#` comments there cost nothing.
- **GENERATED-file notices** are placed where they cost no runtime tokens: YAML frontmatter comments for Claude/Gemini `pr-reviewer-*.md`, a `#` comment for Codex `pr_reviewer_*.toml`. Codex `SKILL.md` files intentionally carry no notice (raw injection would bill it) — the adjacent `skill_head.md` sources and this file are the edit guard. Do not add visible-body notices to generated files.
- **Verify regeneration before committing generated outputs**: when a change touches a generated committed output (Codex `SKILL.md`s, `_AGENTS.md`, pr-reviewer / config-auditor agents), re-run its generator and confirm `git diff` on that file is clean — a dirty diff means the output was edited instead of its source.

## Commit Message Convention

A `commit-msg` hook enforces commitizen (czg) + commitlint; non-conforming commits are rejected.

### Format

```
<type>(<scope>): <emoji> <subject>
```

Example: `perf(claude): ⚡ pr-review-subagentsスキルで止まりにくくする`

### Allowed Types and Scopes

The canonical source is `.commitlintrc.json`:
- Types: `rules.type-enum`
- Scopes: `rules.scope-enum`

Do not duplicate the allowed lists here. When changing types or scopes, update `.commitlintrc.json` first; align `.czrc` type prompts only when type values change.

### Rules

- **scope is required** — empty scope will be rejected
- **subject**: 1–50 characters, must NOT start with an uppercase letter
- **emoji**: czg auto-prepends it; manual commits must include the appropriate emoji at the start of the subject
