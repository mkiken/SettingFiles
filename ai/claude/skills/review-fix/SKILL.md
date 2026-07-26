---
allowed-tools: Bash(gh:*), Bash(git:*), Bash(/bin/cat:*), Bash(ls:*), Bash(mkdir:*), Bash(bash ~/.config/ai-pr/bin/ai_review_run_dir.sh:*), Read, Edit, Write, Glob, Grep, Task
description: "Fix adopted review items from a merge run directory in the working tree, via parallel design subagents and serial implementation subagents"
argument-hint: "[runDir] [itemNumbers...]"
disable-model-invocation: true
---

Parse `$ARGUMENTS`: a token containing `/` is <RUN_DIR>; numeric tokens (space/comma separated) are <ITEM_NUMBERS>. If <RUN_DIR> is absent, resolve the current branch's PR via `gh pr view --json number --jq .number` and run `bash ~/.config/ai-pr/bin/ai_review_run_dir.sh --latest <PR_NUMBER>`.

For every user confirmation (initial selection, resume-or-discard, each rolling design confirmation — options 承認 / 修正依頼 / スキップ, with 修正依頼 feedback collected as free text), use the AskUserQuestion tool.

Subagent launch: use the Task tool (subagent_type: general-purpose). Keep each prompt to a few lines — do not embed the role text: "Read `~/.claude/common/review_fix_subagents/designer_core.md` (or `implementer_core.md`) and follow it. Payload: ...". Launch all design tasks simultaneously and handle each completion as it returns; run implementation tasks one at a time.

!`/bin/cat ~/.claude/common/review_fix_core.md`
