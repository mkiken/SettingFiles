---
allowed-tools: Bash(gh:*), Bash(git:*), Bash(/bin/cat:*), Bash(ls:*), Bash(python3:*), Bash(open:*), Bash(printenv:*), Bash(bash ~/.config/ai-pr/bin/ai_review_run_dir.sh:*), Read, Write, Glob
description: "Merge multi-AI PR review result files into merged.json and an HTML report"
argument-hint: "[runDir]"
disable-model-invocation: true
---

Parse `$ARGUMENTS`: the first token, if present, is <RUN_DIR>. If absent, resolve the current branch's PR via `gh pr view --json number --jq .number` and run `bash ~/.config/ai-pr/bin/ai_review_run_dir.sh --latest <PR_NUMBER>` to get <RUN_DIR>.

!`/bin/cat ~/.claude/common/review_merge_core.md`
