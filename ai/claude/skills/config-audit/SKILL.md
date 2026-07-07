---
description: >
  Audit all Claude Code configuration files for redundancy, conflicts, ambiguity,
  and unnecessary rules.
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

### Launch

In Phase 2, start all six simultaneously with the payload defined there:

1. **config-auditor-default** — デフォルト動作との重複
2. **config-auditor-conflict** — コンフリクト
3. **config-auditor-overlap** — ルール間の重複
4. **config-auditor-patch** — 一時的な修正
5. **config-auditor-ambiguity** — 曖昧なルール
6. **config-auditor-concise** — 意味を変えないトークン削減

## Core Workflow

!`/bin/cat ~/.claude/common/config_audit_subagents/orchestrator_core.md`
