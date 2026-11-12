---
name: audit-fix
allowed-tools: Bash(bash ~/.config/ai-pr/bin/ai_audit_run_dir.sh:*), Bash(/bin/cat:*), Bash(ls:*), Bash(mkdir:*), Bash(git diff:*), Read, Edit, Write, Glob, Grep, Task
description: "Apply the config-audit items decided 適用する in an audit run directory: diffs mechanically, null-diff rewrites through design subagents"
argument-hint: "[platform: claude|codex|gemini] [runDir]"
model: sonnet
disable-model-invocation: true
---

Parse `$ARGUMENTS`: a token containing `/` is <RUN_DIR>; `claude`, `codex`, or `gemini` is <PLATFORM> (default `claude`). If <RUN_DIR> is absent, run `bash ~/.config/ai-pr/bin/ai_audit_run_dir.sh --latest <PLATFORM>` — it prints the newest run directory and never creates one.

Confirmations: resume-or-discard, the single selection confirmation, and each rolling design confirmation (承認 / 修正依頼 / スキップ, with 修正依頼 feedback collected as free text).

Subagent launch: use the Task tool with subagent_type `audit-fix-considerer` / `audit-fix-designer` / `audit-fix-implementer` — their role instructions and their models are baked into their definitions, so pass only the payload each role defines and never substitute `general-purpose`. Launch all consider tasks simultaneously, then all design tasks simultaneously and handle each completion as it returns; implementers run one per group, serialized wherever the overlap rule applies.

In plan mode, run only Item Selection and read any existing `apply_state.json` (ask resume-or-discard, but defer the discard). Write the plan file: the apply items in the Selection Confirmation format with their risk warnings, plus the consider items as pending AI review. Then call ExitPlanMode — spawn no subagent and write nothing but the plan file before approval. After approval, continue from Consider Review. With no consider item, the approval replaces the single selection confirmation; otherwise run the Selection Confirmation after Consider Review, since consider approvals change the selection.

Never run the built-in `doctor` skill or the `claude-api` skill's `prompt-audit` subcommand in this session. Once the session's commit/push flow has finished (or the user declined it), end by telling the user to run them next as separate follow-ups: `doctor` first (operational health: installation duplicates, unused skills/MCP servers/plugins, slow hooks, version currency, permission posture), then `prompt-audit` over the config files this run audited (read-only; finds text written for older models). Both decide in the conversation while the config-audit report decides in the browser — incompatible decision models that must never share a pass.

!`/bin/cat ~/.claude/common/audit_fix_core.md`
