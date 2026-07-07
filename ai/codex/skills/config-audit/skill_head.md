---
name: config-audit
description: >
  Audit all Codex configuration files (AGENTS.md, config.toml, skills, agents,
  hooks, rules) for redundancy, conflicts, ambiguity, and unnecessary rules.
  Trigger keywords: "設定を監査", "コンフィグ監査", "設定の整理", "AGENTS.md最適化",
  "audit config", "clean up config", "check for conflicts", "optimize prompts".
---

## Instructions

- `PLATFORM_NAME` = `Codex`.
- `SCOPE` = the scope keyword in the user's message (empty → `all`).
- `ENTRY_SCOPE` = `agents-md`.
- `GENERATED_ENTRY_FILE` = `~/.codex/AGENTS.md`.
- `CONFIG_PATHS`:
  - Global: `~/.codex/AGENTS.md`, `~/.codex/config.toml`, `~/.codex/skills/*/SKILL.md`, `~/.codex/agents/*.toml`, `~/.codex/hooks.json`, `~/.codex/hooks/*`, `~/.codex/rules/*`
  - Project: `./AGENTS.md`, `./ai/codex/config.toml`, `./ai/codex/codex_base.md`, `./ai/codex/skills/*/skill_head.md`, `./ai/codex/agents/*.toml`, `./ai/codex/hooks.json`, `./ai/codex/rules/*`
  - Never audit runtime/state files under `~/.codex` (auth.json, history.jsonl, sessions/, cache, sqlite, logs).
- `SOURCE_FILES`: `ai/common/prompt_base.md`, `ai/common/characters/nyaruko.md`, `ai/codex/codex_base.md` (concatenated into the generated `_AGENTS.md`; audit the sources, not the generated file)
- For every user confirmation, ask a plain question and wait for the reply.

## Core Workflow
