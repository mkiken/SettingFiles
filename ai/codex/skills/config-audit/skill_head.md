---
name: config-audit
description: >
  Audit all Codex configuration files (AGENTS.md, config.toml, skills, agents,
  hooks, rules) for redundancy, conflicts, ambiguity, and unnecessary rules.
---

## Instructions

- `PLATFORM_NAME` = `Codex`.
- `SCOPE` = the scope keyword in the user's message (empty → `all`).
- `ENTRY_SCOPE` = `agents-md`.
- `GENERATED_ENTRY_FILE` = `~/.codex/AGENTS.md`.
- `RUN_DIR` = output of `bash ~/.config/ai-pr/bin/ai_audit_run_dir.sh codex` (resolve once in Phase 4; `--latest codex` reuses the newest).
- `platform_key` = `codex`.
- `CONFIG_PATHS`:
  - Global: `~/.codex/AGENTS.md`, `~/.codex/config.toml`, `~/.codex/skills/*/SKILL.md`, `~/.codex/agents/*.toml`, `~/.codex/hooks.json`, `~/.codex/hooks/*`, `~/.codex/rules/*`
  - Project: `./AGENTS.md`, `./ai/codex/config.toml`, `./ai/codex/codex_base.md`, `./ai/codex/skills/*/skill_head.md`, `./ai/codex/agents/*.toml`, `./ai/codex/hooks.json`, `./ai/codex/rules/*`
  - Never audit runtime/state files under `~/.codex` (auth.json, history.jsonl, sessions/, cache, sqlite, logs).
- `SOURCE_FILES`: `ai/common/prompt_base.md`, `ai/common/characters/nyaruko.md`, `ai/codex/codex_base.md` (concatenated into the generated `_AGENTS.md`; audit the sources, not the generated file)
- For every user confirmation, prefer `request_user_input` when all required choices fit within the tool's option limit, passing each required label exactly once. If they exceed the limit, ask in plain text with numbered options.

### Spawn

In Phase 2, dispatch the six auditors in waves sized to the child-agent slots available at runtime.
Do not hard-code a slot count. Wait for each wave before starting the next and retain every valid result.

Treat a capacity error as temporary: wait for an active auditor to finish, then retry the same specialist.
Treat an unavailable registered role as distinct: finish every available specialist, collect the missing
dimensions, and ask once whether to stop safely (recommended) or continue only those dimensions with a
default agent. On approved fallback, read the matching
`~/.codex/agents/config_auditor_<dimension>.toml`, then spawn `agent_type=default` with
`fork_turns=none`. Its self-contained payload must name the dimension, target files, and output format,
and prohibit writes and subagents. If the TOML is missing, the fallback fails, or any result is invalid,
stop without generating a partial audit or report.

The six specialist roles are:

1. **config_auditor_default** — デフォルト動作との重複
2. **config_auditor_conflict** — コンフリクト
3. **config_auditor_overlap** — ルール間の重複
4. **config_auditor_patch** — 一時的な修正
5. **config_auditor_ambiguity** — 曖昧なルール
6. **config_auditor_concise** — 意味を変えないトークン削減

## Core Workflow
