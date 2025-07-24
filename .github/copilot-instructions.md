# Copilot Instructions for SettingFiles

This repository manages personal dotfiles and environment configurations for both macOS and Windows. It uses symbolic links to synchronize settings across tools and platforms. Follow these guidelines to ensure AI agents work productively and safely in this codebase.

## Architecture & Structure
  - `ai/` — AI assistant configs (Claude, Cursor/Roo). Shared prompts in `ai/common/prompt.md`.
  - `mac/` — macOS setup scripts (`initialize`, `update`).
  - `windows/` — Windows setup scripts.
  - `vimfiles/` — Vim/Neovim configs (standard, LazyVim, NvChad).
  - `shell/` — Shell configs (Fish, Zsh, Bash).
  - `submodules/` — Zsh plugins as git submodules.
  - `gitfiles/` — Git tool configs (gitui, lazygit).

## Critical Workflows
  - macOS: `cd mac && ./initialize`
  - Windows: `cd windows && ./initialize.ps1`
  - macOS: `cd mac && ./update`
  - Windows: `cd windows && ./update.ps1`
  - Standard Vim: Use Vundle (`:BundleInstall`)
  - LazyVim/NvChad: Managed via Neovim plugin managers

## Project-Specific Conventions

## Integration Points

## Examples

## References

**REMINDER:** Symlinks are critical. Do not copy files manually. Use scripts for all setup and updates.
---
**Additional instruction for AI agents:**
AI agents must always respond in **Japanese** when working in this repository.
