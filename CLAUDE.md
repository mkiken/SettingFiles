# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a personal dotfiles repository for managing development environment configurations across Mac and Windows platforms. It uses symbolic links to synchronize settings across various tools.

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

### Git Submodules Management
```bash
# Update all submodules
git submodule update --init --recursive
```

## Architecture

### Directory Structure
- `/ai/` - AI assistant configurations (Claude, Cursor/Roo)
  - `common/prompt.md` - Shared character prompt (symlinked to ~/.claude/CLAUDE.md)
  - `claude/settings.json` - Claude-specific settings
- `/mac/` - macOS-specific configurations and scripts
  - `initialize` - Sets up symlinks, installs Homebrew packages, configures tools
  - `update` - Updates packages, plugins, and submodules
- `/windows/` - Windows-specific configurations and scripts
- `/vimfiles/` - Vim/Neovim configurations (standard, LazyVim, NvChad variants)
- `/shell/` - Fish shell configuration
- `/submodules/` - Zsh plugins managed as git submodules
- `/gitfiles/` - Git tools configurations (gitui, lazygit)

### Symlink Strategy
The initialize scripts create symbolic links from this repository to system locations:
- AI configs: `ai/common/prompt.md` → `~/.claude/CLAUDE.md` and `~/.roo/rules/.roorules`
- Shell configs: Repository files → Home directory dotfiles
- Editor configs: Repository files → Application config directories

### Vim Plugin Management
- Standard Vim: Uses Vundle (`:BundleInstall` to update)
- LazyVim: Modern Neovim configuration with lazy.nvim
- NvChad: Feature-rich Neovim configuration

## Important Notes

1. **Symlinks are critical** - The repository works by creating symbolic links. Don't copy files manually.
2. **Platform-specific scripts** - Use the appropriate initialize/update scripts for your OS.
3. **Git submodules** - Many Zsh plugins are managed as submodules. Always update recursively.
4. **AI character prompt** - The repository includes a Nyaruko-san character prompt that affects AI assistant behavior.