---
allowed-tools: Bash(bash ~/.config/ai-pr/bin/ai_audit_run_dir.sh:*), Bash(/bin/cat:*), Bash(ls:*), Bash(mkdir:*), Bash(git diff:*), Read, Edit, Write, Glob, Grep, Task
description: "Apply the config-audit items decided 適用する in an audit run directory: diffs mechanically, null-diff rewrites through design subagents"
argument-hint: "[platform: claude|codex|gemini] [runDir]"
model: sonnet
disable-model-invocation: true
---

Parse `$ARGUMENTS`: a token containing `/` is <RUN_DIR>; `claude`, `codex`, or `gemini` is <PLATFORM> (default `claude`). If <RUN_DIR> is absent, run `bash ~/.config/ai-pr/bin/ai_audit_run_dir.sh --latest <PLATFORM>` — it prints the newest run directory and never creates one.

Confirmations: resume-or-discard, the single selection confirmation, and each rolling design confirmation (承認 / 修正依頼 / スキップ, with 修正依頼 feedback collected as free text).

Subagent launch: use the Task tool with subagent_type `audit-fix-designer` / `audit-fix-implementer` — their role instructions and their models are baked into their definitions, so pass only the payload each role defines and never substitute `general-purpose`. Launch all design tasks simultaneously and handle each completion as it returns; implementers run one per group, serialized wherever the overlap rule applies.

After the core's Finish summary, ask via AskUserQuestion (multiSelect) which follow-ups to run now: the built-in `doctor` skill (operational health: installation duplicates, unused skills/MCP servers/plugins, slow hooks, version currency, permission posture), and the `claude-api` skill's `prompt-audit` subcommand over the config files this run audited (read-only; finds text written for older models). Run only the selected ones, `doctor` first when both; otherwise stop. They run here, after the applied edits, because both decide in the conversation while the config-audit report decides in the browser — incompatible decision models that must never share a pass.

!`/bin/cat ~/.claude/common/audit_fix_core.md`
