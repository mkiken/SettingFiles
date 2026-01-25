# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Personal dotfiles repository for managing development environment configurations across Mac and Windows. Uses symbolic links to synchronize settings.

## Key Commands

### Initial Setup
```bash
# Mac
cd mac && ./initialize

# Windows (PowerShell)
cd windows
./initialize.ps1
```

### Update Environment
```bash
# Mac
cd mac && ./update

# Windows (PowerShell)
cd windows
./update.ps1
```

### Homebrew Package Management
```bash
# Install packages from Brewfile
cd mac && brew bundle

# Add new package: edit mac/Brewfile, then run brew bundle
```

### Git Submodules
```bash
git submodule update --init --recursive
```

## Architecture

### Directory Structure
- `/ai/` - AI assistant configurations
  - `common/prompt_base.md` - Shared base prompt
  - `common/characters/` - Character prompts (reimu.md for Claude, nyaruko.md for Gemini)
  - `common/mcp.json` - MCP server settings
  - `claude/` - Claude Code settings, commands, hooks
  - `gemini/` - Gemini CLI settings, commands
  - `serena/serena_config.yml` - Serena MCP configuration
- `/mac/` - macOS configurations and scripts
  - `initialize` → `initialization/initialize` (6-step setup)
  - `update` - Package/plugin update script
  - `Brewfile` - Homebrew package declarations
- `/windows/` - Windows configurations and scripts
- `/vimfiles/nvim/` - Neovim configuration (lazy.nvim)
- `/shell/zsh/` - Zsh configuration with znap plugin manager
- `/submodules/` - Git submodule-managed Zsh plugins
- `/gitfiles/` - Git configurations (gitui, lazygit, gh-dash, workmux)
- `/terminal/` - Terminal emulator configs (ghostty, etc.)

### Symlink Strategy
Initialize scripts create symbolic links from repository to system locations:
- AI configs: `ai/claude/_CLAUDE.md` → `~/.claude/CLAUDE.md`
- Shell configs: `shell/zsh/.zshrc` → `~/.zshrc`
- Editor configs: `vimfiles/nvim` → `~/.config/nvim`
- Git configs: `gitfiles/.gitconfig` → `~/.gitconfig`

### AI Configuration Generation
Claude prompt is assembled from multiple sources:
- `ai/common/prompt_base.md` + `ai/common/characters/reimu.md` + `ai/claude/claude_prompt.md` → `ai/claude/_CLAUDE.md`
- The generated `_CLAUDE.md` is symlinked to `~/.claude/CLAUDE.md`
- Same pattern for Gemini with `nyaruko.md` character

### Plugin Management

**Zsh (znap)**:
- Config: `shell/zsh/plugin.zsh`
- Plugins: fzf-tab, zsh-autosuggestions, F-Sy-H, zsh-vi-mode

**Neovim (lazy.nvim)**:
- Config: `vimfiles/nvim/lua/config/lazy.lua`
- Plugins: `vimfiles/nvim/lua/plugins/`
- VSCode Neovim uses separate plugin set: `plugins_vscode/`
- Versions locked in `lazy-lock.json`

## AI Prompt File Editing

When editing AI prompt files in this repository:

- **Default to English** for new content and modifications
  - Reason: Reduces token consumption for efficiency
- **Exception**: If the original file uses a different language, follow that language
  - Example: Japanese character dialogue examples should remain in Japanese

## Important Notes

1. **Symlinks are critical** - Don't copy files manually; the repository works via symbolic links
2. **Platform-specific scripts** - Use appropriate initialize/update scripts for your OS
3. **Git submodules** - Zsh plugins managed as submodules; always update recursively
4. **AI prompts include character settings** - 博麗霊夢 (Hakurei Reimu) character for Claude
