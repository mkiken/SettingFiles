---
description: >
  Audit all Claude Code configuration files for redundancy, conflicts, ambiguity,
  and unnecessary rules.
model: fable
argument-hint: "[scope: all|claude-md|skills|agents|hooks|settings|global|project]"
allowed-tools: Bash(/bin/cat:*), Bash(readlink:*), Bash(bash:*), Bash(python3:*), Bash(nohup:*), Bash(curl:*), Bash(open:*), Read, Glob, Grep, Write
---

## Instructions

- `PLATFORM_NAME` = `Claude Code`.
- `SCOPE` = `$ARGUMENTS`.
- `ENTRY_SCOPE` = `claude-md`.
- `GENERATED_ENTRY_FILE` = `~/.claude/CLAUDE.md`.
- `RUN_DIR` = output of `bash ~/.config/ai-pr/bin/ai_audit_run_dir.sh claude` (resolve once in Phase 4; `--latest claude` reuses the newest).
- `platform_key` = `claude`.
- `CONFIG_PATHS`:
  - Global: `~/.claude/CLAUDE.md`, `~/.claude/settings.json`, `~/.claude/settings.local.json`, `~/.claude/skills/*/SKILL.md`, `~/.claude/agents/*.md`, `~/.claude/hooks/*`
  - Project: `./CLAUDE.md`, `./.claude/CLAUDE.md`, `./.claude/settings.json`, `./.claude/settings.local.json`, `./.claude/skills/*/SKILL.md`, `./.claude/agents/*.md`
- `SOURCE_FILES`: `ai/common/prompt_base.md`, `ai/common/genshijin-file-policy.md`, `ai/claude/_CLAUDE.md` (inline extras beyond the @imports)
- For every user confirmation, use `AskUserQuestion`.

### Launch

In Phase 2, start all six simultaneously with the payload defined there:

1. **config-auditor-default** — デフォルト動作との重複
2. **config-auditor-conflict** — コンフリクト
3. **config-auditor-overlap** — ルール間の重複
4. **config-auditor-patch** — 一時的な修正
5. **config-auditor-ambiguity** — 曖昧なルール
6. **config-auditor-concise** — 意味を変えないトークン削減

## Related: operational health

This skill audits configuration *content* only. Installation duplicates, unused
skills/MCP servers/plugins, slow hooks, version currency, and permission posture belong to
the built-in `doctor` skill. The two use incompatible decision models — `doctor` decides in
the conversation, this skill decides in the browser report — so never run them in the same
pass. Apply this skill's decisions with `audit-fix` first, then run `doctor` separately if
the user wants the operational side checked. Name it in the Phase 4 summary as an optional
follow-up, not as part of this run.

## Core Workflow

!`/bin/cat ~/.claude/common/config_audit_subagents/orchestrator_core.md`
