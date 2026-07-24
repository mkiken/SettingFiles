# CLAUDE.md

Guidance for AI coding agents working in this repository. Root `AGENTS.md` is a symlink to this file (Codex reads the same content) — keep instructions platform-neutral (no agent-specific plugin or skill references).

## Repository Overview

Personal dotfiles for Mac and Windows development environments, synchronized via symbolic links.

## Repository Branch Policy

Implementation work may start directly on `main`/`master`; when a workflow or skill requires explicit consent for that, treat this section as standing consent. It covers only starting implementation in place — never skip separately required confirmation flows for destructive or side-effecting operations (commits, pushes, pull requests, deletes, deployments, external API writes).

Multiple agent sessions can run against this repository concurrently (e.g. one session renaming a function while another writes new code that calls it). Immediately before committing, run `git fetch origin <branch>` and compare against `origin/<branch>`; if the remote has commits not yet in the local history, inspect them (`git log`/`git show`) for overlap with files this session touched before committing, since a same-file dependency (a rename one session made vs. a call site another session wrote) can integrate correctly by coincidence or silently break.

When a file mixes this session's changes with another session's unrelated in-progress edits, and only this session's hunks are staged (e.g. via a rebuilt index blob), do not run `git commit -- <paths>`: pathspec-scoped commit ignores the partially staged index for that path and instead commits the working tree's current content, silently pulling in the other session's unstaged changes. Verify `git diff --cached` matches intent, then commit with no pathspec.

## CLAUDE.md Maintenance

At implementation completion, before the commit confirmation in the post-implementation flow, check whether the work surfaced repository knowledge that materially changes how future work should be performed: architecture or workflow changes, durable conventions or pitfalls, operational commands, or existing statements the work proved stale or contradicted. Do not add isolated interactive aliases or implementation details that are readily discoverable from source. If so, draft the addition or correction, present it to the user for approval, and edit this file only when approved — never silently. Niche, domain-specific knowledge not needed for broad work belongs in a project skill, not this file: for domains already extracted (Herdr integration, notification hooks, GSD Core — see the project-skills paragraph under Symlink Strategy) propose the addition to the matching skill; for a new such domain, propose a new `.claude/skills/<name>/SKILL.md`. Keep this file to broadly-relevant guidance, and when working in a skill-covered domain start by reading its `SKILL.md`. Proposing before the commit confirmation lets an approved change land in the same commit. If nothing qualifies, propose nothing.

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

### Run Tests
```bash
python3 -m unittest discover -s tests
```
Run before committing code changes (the suite takes seconds). Fix failures, or report them explicitly at the commit confirmation — never leave the suite red.

Shell functions (e.g. those in `shell/tmux/ai_notification_*.sh`) are unit-tested from Python: a `tests/test_*.py` `source`s the `.sh` and invokes the function via `bash -c`, asserting on stdout and the return code (see `tests/test_ai_notification_summary.py` for the `run_fn` helper pattern). Write new shell-function tests in this style so `unittest discover` collects them — a standalone `.sh` test file is not picked up by the suite.

Before changing notification hooks or their tests (`ai/*/hooks/`, `shell/tmux/ai_notification_*`), read `.claude/skills/ai-notification-hooks/SKILL.md` — it defines required domain tests beyond the main suite.

### Regenerate AI Prompts

Canonical source-to-command mapping for regenerating committed outputs. The full init scripts (`mac/initialization/ai/{claude,gemini,codex}.sh`) cover everything; the targeted commands below are faster.

| Edited source | Regenerate with |
| --- | --- |
| `ai/common/prompt_base.md`, `ai/common/characters/*.md` (Claude/Gemini load these at runtime via `@file`) | Codex only: `zsh -c 'source mac/scripts/common.sh && generate_codex_agents'` |
| `ai/codex/codex_base.md` | `zsh -c 'source mac/scripts/common.sh && generate_codex_agents'` |
| Shared-core skill sources (`ai/common/*_core.md`, `ai/{codex,gemini}/skills/*/skill_head.md`/`skill_tail.md`; includes pr-review-subagents skill adapters) | `zsh -c 'source mac/scripts/common.sh && verify_ai_skill_generation_idempotency'` |
| pr-reviewer agent sources (`ai/common/pr_review_subagents/intro_*.md`, `ai/common/pr_review_subagents/format_*.md`, `ai/*/agents_src/`) | `zsh -c 'source mac/scripts/common.sh && generate_pr_reviewer_agents <platform>'` |
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

When adding a managed symlink, apply it to the live environment and verify it with `readlink`; if the target exists unexpectedly, stop and report it instead of overwriting it.

When adding a new initialization step to `mac/initialization/`, `mac/updates/`, or `mac/scripts/ai/` setup functions, ask the user whether re-running it on an already-initialized environment should skip the step (an idempotency guard) before implementing it — a step that re-runs unconditionally can corrupt state it already wrote (e.g. duplicate plugin registrations) on a repeated `mac/initialize`.

When editing shell helpers, do not use global variables for temporary return values or cross-call state. Prefer stdout, explicit arguments, or safe assignment into caller-owned `local` variables so parallel shells and nested calls cannot observe stale state.

In zsh, `path` is a special array tied to `PATH`; never use it as a local or temporary variable name in shell helpers.

In interactive shells, `cd` fires chpwd hooks (their stdout pollutes command substitutions) and is overridden by zoxide's `cd` function which rejects `-q`; shell helpers that cd inside `$(...)` must use `builtin cd -q`.

Files sourced during zshrc init (e.g. `shell/zsh/filter/base.zsh`) must bail out with `return`, never `exit` — `exit` kills the whole shell mid-init with no visible error (a Herdr popup running `zsh -ic` then closes instantly before the `-c` command ever runs).

Key symlinks:
- `ai/claude/_CLAUDE.md` → `~/.claude/CLAUDE.md`
- `ai/gemini/_GEMINI.md` → `~/.gemini/GEMINI.md`
- `ai/codex/_AGENTS.md` → `~/.codex/AGENTS.md`
- `~/.zshrc` loads `shell/zsh/managed.zsh` through a managed loader block
- `vimfiles/nvim` → `~/.config/nvim`
- `gitfiles/.gitconfig` → `~/.gitconfig`

### No Personal Paths
Never hardcode a user-specific absolute path (e.g. `/Users/<name>/…`, a real home directory, or an account-name-derived path) in committed sources — scripts, tests, fixtures, or config. Use `$HOME`/`~`, `$SET`, a repo-root-relative path, or a clearly generic placeholder (`/Users/testuser/…`) instead. Machine- or account-specific values belong in un-tracked `*.local` files, not the repository.

When moving or removing tmux key bindings, `source-file` does not clear old bindings; explicitly `unbind` old keys and verify the live state with `tmux list-keys`.

Before working on Herdr keybindings or popups (`terminal/herdr/config.toml`, `[[keys.command]]`), read `.claude/skills/herdr-dev/SKILL.md` first.

Claude-specific files (agents, hooks, scripts) are individually symlinked into `~/.claude/`. Claude has no custom slash commands — former commands live as skills under `ai/claude/skills/`.

Skills (`ai/common/skills/`, `ai/{claude,gemini,codex}/skills/`) are symlinked per directory into `~/.<platform>/skills/` via `setup_ai_skills`, so skill edits take effect immediately — except generated `SKILL.md` files (all Codex shared-core skills and Gemini fact-based), which must be regenerated from their sources (see "Regenerate AI Prompts" under Key Commands). The whole `ai/common` directory is also symlinked to `~/.gemini/common` and `~/.claude/common` for runtime file references — Claude and Gemini only; Codex has no `~/.codex/common`. Python modules shared by the platform hooks therefore live in `shell/tmux/` (e.g. `tmux_emoji.py`, `tmux_window_name.py`); hooks reach them because `Path(__file__).resolve()` dereferences the hook symlink back into the repo.

Repository-local domain-knowledge skills live in `.claude/skills/<name>/SKILL.md` (currently `herdr-dev`, `ai-notification-hooks`, `gsd-core-setup`); each `.agents/skills/<name>` is a committed relative symlink to the same directory so Codex discovers them too. No build step — edit the `.claude/skills/` source directly (frontmatter must stay in the cross-platform subset: `name` + `description` only, no runtime includes).

`ai/claude/settings.json` and `ai/gemini/settings.json` are the exception: not symlinked but deep-merged into `~/.claude/settings.json` / `~/.gemini/settings.json` via `smart_merge_json`, and the files diverge (the live files accumulate machine-local keys). Editing the repository source alone does not update the live file — apply with `mac/initialization/ai/{claude,gemini}.sh` / `mac/update`, or merge manually for immediate effect. Merging only adds or updates keys: removing an entry (e.g. deleting a hook registration) never propagates, so also delete it from the live file by hand.

`ai/codex/config.toml` is also not symlinked: full Codex initialization and update merge it into `~/.codex/config.toml` via `smart_merge_toml`. Editing only the repository source does not update the live file. For a targeted immediate update, run the interactive merge directly: `zsh -c 'source mac/scripts/common.sh && smart_merge_toml "${Repo}ai/codex/config.toml" "$HOME/.codex/config.toml"'`.

### AI Configuration Generation
Throughout this section: edit the sources, never the generated committed outputs — regenerate via the "Regenerate AI Prompts" table under Key Commands.

Both `_CLAUDE.md` and `_GEMINI.md` are static files using `@file` import syntax to compose prompts from shared source files at runtime:
- **Claude** (`ai/claude/_CLAUDE.md`): `@../common/prompt_base.md` + `@../common/characters/reimu.md`
- **Gemini** (`ai/gemini/_GEMINI.md`): `@../common/prompt_base.md` + `@../common/characters/rikka_takanashi.md` + inline Language rules

Edit these sources directly — no build step. Gemini additionally merges `ai/common/mcp.json` (and `mcp.local.json` if present) into its `settings.json`.

- **Codex** (`ai/codex/_AGENTS.md`): Codex's AGENTS.md does not support `@file` imports, so `mac/initialization/ai/codex.sh` (and `mac/updates/codex.sh`) generates `_AGENTS.md` by `cat`-concatenating `ai/common/prompt_base.md` + `ai/common/characters/nyaruko.md` + `ai/codex/codex_base.md`; the generated file is committed and symlinked to `~/.codex/AGENTS.md`.

`ai/common/characters/` is a swappable persona palette: reimu (Claude), rikka_takanashi (Gemini), and nyaruko (Codex) are currently wired; hestia, mizuki_himeji, and nagato_yuki are intentional alternates kept for swapping, not dead files.

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

Standalone skills (no shared core, hand-maintained): `web-summary` — Claude `ai/claude/skills/web-summary/SKILL.md` and Gemini `ai/gemini/commands/web-summary.toml` are a manually synchronized pair with no generator (editing one does not update the other); `prompt-self-improvement` — single shared source in `ai/common/skills/`, symlink-deployed to all three platforms; `herdr` — single shared source in `ai/common/skills/`, symlink-deployed to all three platforms, vendored from the official herdr `SKILL.md` (teaches an agent to operate the `herdr` CLI from inside a Herdr-managed pane; guarded by a `HERDR_ENV=1` check so it is a no-op outside Herdr); `skill-creator` and `write-tests` — Claude-only, in `ai/claude/skills/`.

### Claude Hooks
Notification-hook roles and implementation rules for all three platforms live in `.claude/skills/ai-notification-hooks/SKILL.md` — read it before changing `ai/*/hooks/` or `shell/tmux/ai_notification_*`.

### Plugin Management

**Zsh (znap)**: Config in `shell/zsh/plugin.zsh`. Plugins updated via `znap pull` in `mac/update` (submodule/runtime split: see Directory Structure).

**Neovim (lazy.nvim)**: Plugins in `vimfiles/nvim/lua/plugins/`. VSCode Neovim uses separate `plugins_vscode/`. Updated via `nvim --headless "+Lazy! sync | TSUpdate" +qa` in `mac/update`.

**GSD Core**: before changing GSD Core setup (`setup_gsd_core_for_runtime`, the managed `~/.codex/hooks.json`, the Claude permission fix), read `.claude/skills/gsd-core-setup/SKILL.md`.

**Herdr integrations**: before changing Herdr integration (`mac/scripts/herdr.sh`, Herdr plugins such as notify-rich, Gemini's Herdr notification split, shell status icon mirroring), read `.claude/skills/herdr-dev/SKILL.md`. Never run `herdr integration install` against live Claude or Codex configuration; always use the repository helper.

## AI Prompt File Editing

When editing AI prompt files in this repository:

- **Default to English** for new or modified content (reduces token consumption); if the original file uses a different language, follow it (e.g. Japanese character dialogue examples)
- **Write concisely**: as concise as meaning and intent allow — every loaded prompt consumes context. When condensing existing files, follow `ai/common/prompt_shortening_guide.md`.
- **Runtime loading differs per platform**: Claude Code and Gemini CLI load only the markdown body of agent/skill files as the prompt — frontmatter (including YAML `#` comments) costs zero runtime tokens. Codex instead injects the whole SKILL.md raw at invocation, so every Codex skill frontmatter line counts as prompt cost. Codex agent TOML files are parsed; `#` comments there cost nothing.
- **GENERATED-file notices** are placed where they cost no runtime tokens: YAML frontmatter comments for Claude/Gemini `pr-reviewer-*.md`, a `#` comment for Codex `pr_reviewer_*.toml`. Codex `SKILL.md` files intentionally carry no notice (raw injection would bill it) — the adjacent `skill_head.md` sources and this file are the edit guard. Do not add visible-body notices to generated files.
- **Verify regeneration before committing generated outputs**: for shared-core skills, use `verify_ai_skill_generation_idempotency` from the regeneration table; it generates twice and fails if any SHA-256 changes. For other generators, after updating sources and running the generator once, record each generated output's hash, re-run the generator, and confirm the hash is unchanged. The output may legitimately differ from `HEAD`; review that diff separately. A changed hash on the second run means the first output was stale or generation is not idempotent.

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
