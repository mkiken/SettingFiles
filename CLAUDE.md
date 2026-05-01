# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Personal dotfiles repository for managing development environment configurations across Mac and Windows. Uses symbolic links to synchronize settings.

## Key Commands

### Initial Setup
```bash
# Mac (7-step setup: copy_files → homebrew → dev_tools → notify_icons → git_setup → system_setup → AI assistants)
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
- `shell/zsh/.zshrc` → `~/.zshrc`
- `vimfiles/nvim` → `~/.config/nvim`
- `gitfiles/.gitconfig` → `~/.gitconfig`

Claude-specific files (commands, hooks) are individually symlinked into `~/.claude/`. Commands go to `~/.claude/commands/my/`.

### AI Configuration Generation
Both `_CLAUDE.md` and `_GEMINI.md` are static files using `@file` import syntax to compose prompts from shared source files at runtime:
- **Claude** (`ai/claude/_CLAUDE.md`): `@../common/prompt_base.md` + `@../common/characters/reimu.md`
- **Gemini** (`ai/gemini/_GEMINI.md`): `@../common/prompt_base.md` + `@../common/characters/nyaruko.md` + inline Language rules

Edit the source files directly (`ai/common/prompt_base.md`, `ai/common/characters/*.md`) — no build step needed. Gemini additionally merges `ai/common/mcp.json` (and `mcp.local.json` if present) into its `settings.json`.

- **Codex** (`ai/codex/_AGENTS.md`): Codex's AGENTS.md does not support `@file` imports, so `mac/initialization/ai/codex.sh` (and `mac/updates/codex.sh`) generates `_AGENTS.md` by `cat`-concatenating `ai/common/prompt_base.md` + `ai/common/characters/reimu.md`. The generated file is committed and symlinked to `~/.codex/AGENTS.md`. Edit the source files (not the generated `_AGENTS.md`); regenerate with `mac/initialization/ai/codex.sh`.

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
