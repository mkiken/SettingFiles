---
allowed-tools: Bash(gh:*), Bash(diff:*), Bash(tr:*), Bash(rm:*), Bash(/bin/cat:*), Write
description: "Generate comprehensive PR body content using gh command for specified PR number"
argument-hint: [prNumber]
---

## Instructions

- In the rules below, `<PR_NUMBER>` refers to $ARGUMENTS.
- Fetch the existing PR body with `gh pr view $ARGUMENTS --json body`, then fetch and analyze the full diff with `gh pr diff $ARGUMENTS`. Check whether `.github/PULL_REQUEST_TEMPLATE.md` exists in the repository root.
- Write `pr_body_new.md` with the Write tool.
- Ask the confirmation question with AskUserQuestion.

!`/bin/cat ~/.claude/common/pr_body_core.md`
