---
allowed-tools: Bash(gh:*), Bash(git:*), Bash(/bin/cat:*), Bash(ls:*), Bash(bash ~/.config/ai-pr/bin/ai_review_run_dir.sh:*), Read, Edit, Write, Glob, Grep
description: "Fix adopted review items from a merge run directory in the working tree"
argument-hint: "[runDir] [itemNumbers...]"
disable-model-invocation: true
---

Parse `$ARGUMENTS`: a token containing `/` is <RUN_DIR>; numeric tokens (space/comma separated) are <ITEM_NUMBERS>. If <RUN_DIR> is absent, resolve the current branch's PR via `gh pr view --json number --jq .number` and run `bash ~/.config/ai-pr/bin/ai_review_run_dir.sh --latest <PR_NUMBER>`.

For the pre-edit confirmation, use the AskUserQuestion tool.

!`/bin/cat ~/.claude/common/review_fix_core.md`
