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
# Mac (submodules, brew, npm, pipx, AI tools, nvim plugins, znap, gh extensions, zcompile)
cd mac && ./update

# Windows (PowerShell)
cd windows && ./update.ps1
```

### Homebrew Package Management
```bash
cd mac && brew bundle
```

### Git Submodules
```bash
git submodule update --init --recursive
```

## Architecture

### Directory Structure
- `/ai/` - AI assistant configurations (Claude, Gemini, Serena)
- `/mac/` - macOS configurations, initialization, and update scripts
- `/windows/` - Windows configurations and scripts
- `/vimfiles/nvim/` - Neovim configuration (lazy.nvim)
- `/shell/zsh/` - Zsh configuration with znap plugin manager
- `/submodules/` - Git submodule-managed Zsh plugins
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
- `shell/zsh/.zshrc` → `~/.zshrc`
- `vimfiles/nvim` → `~/.config/nvim`
- `gitfiles/.gitconfig` → `~/.gitconfig`

Claude-specific files (agents, commands, hooks, skills) are individually symlinked into `~/.claude/`. Commands go to `~/.claude/commands/my/`, skills are symlinked as directories.

### AI Configuration Generation
AI prompts are assembled by concatenating multiple source files:
- **Claude**: `ai/common/prompt_base.md` + `ai/common/characters/reimu.md` + `ai/claude/claude_prompt.md` → `ai/claude/_CLAUDE.md`
- **Gemini**: `ai/common/prompt_base.md` + `ai/common/characters/nyaruko.md` + `ai/gemini/gemini_prompt.md` → `ai/gemini/_GEMINI.md`

The generated `_CLAUDE.md` / `_GEMINI.md` files are gitignored outputs — **edit the source files, not the generated files**. Gemini additionally merges `ai/common/mcp.json` (and `mcp.local.json` if present) into its `settings.json`.

To regenerate after editing source files: re-run `mac/initialization/ai/claude.sh` or `mac/initialization/ai/gemini.sh`.

### Plugin Management

**Zsh (znap)**: Config in `shell/zsh/plugin.zsh`. Plugins updated via `znap pull` in `mac/update`.

**Neovim (lazy.nvim)**: Plugins in `vimfiles/nvim/lua/plugins/`. VSCode Neovim uses separate `plugins_vscode/`. Updated via `nvim --headless "+Lazy! sync | TSUpdate" +qa` in `mac/update`.

## AI Prompt File Editing

When editing AI prompt files in this repository:

- **Default to English** for new content and modifications (reduces token consumption)
- **Exception**: If the original file uses a different language, follow that language (e.g., Japanese character dialogue examples)

## Important Notes

- **Symlinks are critical** - Don't copy files manually; the repository works via symbolic links
- **Git submodules** - Zsh plugins managed as submodules; always update recursively
- **AI prompts include character settings** - 博麗霊夢 (Hakurei Reimu) for Claude, ニャル子 for Gemini
