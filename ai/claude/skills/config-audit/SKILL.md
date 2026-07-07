---
description: >
  Audit all Claude Code configuration files for redundancy, conflicts, ambiguity,
  and unnecessary rules. Analyzes CLAUDE.md, skills, commands, agents, hooks, and
  settings across global (~/.claude/) and project-level configs. Use when the user
  wants to clean up config, check for conflicts, optimize prompts, or reduce token
  consumption. Trigger keywords: "設定を監査", "コンフィグ監査", "設定の整理",
  "ルールの重複チェック", "CLAUDE.md最適化", "audit config", "clean up config",
  "check for conflicts", "optimize prompts", "config redundancy", "設定ファイルを整理",
  "CLAUDE.mdを最適化".
model: opus
argument-hint: "[scope: all|claude-md|skills|agents|hooks|settings|global|project]"
allowed-tools: Bash(/bin/cat:*), Bash(readlink:*), Read, Glob, Grep
---

## Instructions

- `PLATFORM_NAME` = `Claude Code`.
- `SCOPE` = `$ARGUMENTS`.
- `ENTRY_SCOPE` = `claude-md`.
- `GENERATED_ENTRY_FILE` = `~/.claude/CLAUDE.md`.
- `CONFIG_PATHS`:
  - Global: `~/.claude/CLAUDE.md`, `~/.claude/settings.json`, `~/.claude/settings.local.json`, `~/.claude/skills/*/SKILL.md`, `~/.claude/agents/*.md`, `~/.claude/hooks/*`
  - Project: `./CLAUDE.md`, `./.claude/CLAUDE.md`, `./.claude/settings.json`, `./.claude/settings.local.json`, `./.claude/skills/*/SKILL.md`, `./.claude/agents/*.md`
- `SOURCE_FILES`: `ai/common/prompt_base.md`, the character file `@`-imported by `ai/claude/_CLAUDE.md`, `ai/claude/_CLAUDE.md` (inline extras beyond the @imports)
- For every user confirmation, use `AskUserQuestion`.

## Core Workflow

!`/bin/cat ~/.claude/common/config_audit_core.md`
