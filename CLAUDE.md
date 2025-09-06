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

# ═══════════════════════════════════════════════════
# Claude Code Spec-Driven Development
# ═══════════════════════════════════════════════════

Kiro-style Spec Driven Development implementation using claude code slash commands, hooks and agents.

## Project Context

### Paths
- Steering: `.kiro/steering/`
- Specs: `.kiro/specs/`
- Commands: `.claude/commands/`

### Steering vs Specification

**Steering** (`.kiro/steering/`) - Guide AI with project-wide rules and context
**Specs** (`.kiro/specs/`) - Formalize development process for individual features

### Active Specifications
- Check `.kiro/specs/` for active specifications
- Use `/kiro:spec-status [feature-name]` to check progress

## Development Guidelines
- Think in English, but generate responses in Japanese (思考は英語、回答の生成は日本語で行うように)

## Workflow

### Phase 0: Steering (Optional)
`/kiro:steering` - Create/update steering documents
`/kiro:steering-custom` - Create custom steering for specialized contexts

**Note**: Optional for new features or small additions. Can proceed directly to spec-init.

### Phase 1: Specification Creation
1. `/kiro:spec-init [detailed description]` - Initialize spec with detailed project description
2. `/kiro:spec-requirements [feature]` - Generate requirements document
3. `/kiro:spec-design [feature]` - Interactive: "requirements.mdをレビューしましたか？ [y/N]"
4. `/kiro:spec-tasks [feature]` - Interactive: Confirms both requirements and design review

### Phase 2: Progress Tracking
`/kiro:spec-status [feature]` - Check current progress and phases

## Development Rules
1. **Consider steering**: Run `/kiro:steering` before major development (optional for new features)
2. **Follow 3-phase approval workflow**: Requirements → Design → Tasks → Implementation
3. **Approval required**: Each phase requires human review (interactive prompt or manual)
4. **No skipping phases**: Design requires approved requirements; Tasks require approved design
5. **Update task status**: Mark tasks as completed when working on them
6. **Keep steering current**: Run `/kiro:steering` after significant changes
7. **Check spec compliance**: Use `/kiro:spec-status` to verify alignment

## Steering Configuration

### Current Steering Files
Managed by `/kiro:steering` command. Updates here reflect command changes.

### Active Steering Files
- `product.md`: Always included - Product context and business objectives
- `tech.md`: Always included - Technology stack and architectural decisions
- `structure.md`: Always included - File organization and code patterns

### Custom Steering Files
<!-- Added by /kiro:steering-custom command -->
<!-- Format:
- `filename.md`: Mode - Pattern(s) - Description
  Mode: Always|Conditional|Manual
  Pattern: File patterns for Conditional mode
-->

### Inclusion Modes
- **Always**: Loaded in every interaction (default)
- **Conditional**: Loaded for specific file patterns (e.g., `"*.test.js"`)
- **Manual**: Reference with `@filename.md` syntax
