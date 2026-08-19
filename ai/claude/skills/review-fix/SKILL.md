---
allowed-tools: Bash(gh:*), Bash(git:*), Bash(zsh:*), Bash(/bin/cat:*), Bash(ls:*), Bash(mkdir:*), Bash(bash ~/.config/ai-pr/bin/ai_review_run_dir.sh:*), Read, Edit, Write, Glob, Grep, Task
description: "Fix review items marked 修正する in a merge run directory, via parallel design subagents and per-group worktree implementations"
argument-hint: "[runDir] [itemNumbers...]"
disable-model-invocation: true
---

Parse `$ARGUMENTS`: a token containing `/` is <RUN_DIR>; numeric tokens (space/comma separated) are <ITEM_NUMBERS>. If <RUN_DIR> is absent, resolve the current branch's PR via `gh pr view --json number --jq .number` and run `bash ~/.config/ai-pr/bin/ai_review_run_dir.sh --latest <PR_NUMBER>`.

For every user confirmation, use the AskUserQuestion tool: initial selection, resume-or-discard, each rolling design confirmation (承認 / 修正依頼 / スキップ, with 修正依頼 feedback collected as free text), each group's four-choice commit/merge confirmation, and the two-choice merge-conflict confirmation.

<WORKTREE_TASK_DOC> = `~/.claude/skills/worktree-task/SKILL.md`.

Subagent launch: use the Task tool (subagent_type: general-purpose). Keep each prompt to a few lines — do not embed the role text: "Read `~/.claude/common/review_fix_subagents/designer_core.md` (or `implementer_core.md`) and follow it. Payload: ...". Implementer payloads include <WORKTREE_PATH>. Launch all design tasks simultaneously and handle each completion as it returns; implementers may also run in parallel (one per group worktree), but Confirm & Merge stays strictly serial.

!`/bin/cat ~/.claude/common/review_fix_core.md`
