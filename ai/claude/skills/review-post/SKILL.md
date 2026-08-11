---
allowed-tools: Bash(gh:*), Bash(git:*), Bash(/bin/cat:*), Bash(ls:*), Bash(bash ~/.config/ai-pr/bin/ai_review_run_dir.sh:*), Read, Glob
description: "Post adopted review items from a merge run directory as PR review comments"
argument-hint: "[runDir] [itemNumbers...]"
disable-model-invocation: true
---

Parse `$ARGUMENTS`: a token containing `/` is <RUN_DIR>; numeric tokens (space/comma separated) are <ITEM_NUMBERS>. If <RUN_DIR> is absent, resolve the current branch's PR via `gh pr view --json number --jq .number` and run `bash ~/.config/ai-pr/bin/ai_review_run_dir.sh --latest <PR_NUMBER>`.

`{ai_header}` = `🤖 **AI コードレビュー**` — this run merges findings from several AIs, so the header never names the posting AI.

For the final posting confirmation, use the AskUserQuestion tool.

!`/bin/cat ~/.claude/common/review_post_core.md`

!`/bin/cat ~/.claude/common/pr_post_mechanics_core.md`
