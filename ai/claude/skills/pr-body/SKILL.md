---
allowed-tools: Bash(gh:*), Bash(git:*), Bash(diff:*), Bash(tr:*), Bash(trash:*), Bash(mktemp:*), Bash(/bin/cat:*), Write
description: "Generate comprehensive PR body content using gh command for specified PR number"
argument-hint: [prNumber]
disable-model-invocation: true
---

## Instructions

- In the rules below, `<PR_NUMBER>` refers to $ARGUMENTS; if $ARGUMENTS is empty, resolve the current branch's PR number with `gh pr view --json number --jq .number` and use that; if that fails, ask the user for the PR number.
- Fetch the existing PR body and URL with `gh pr view <PR_NUMBER> --json body,url`, then fetch and analyze the full diff with `gh pr diff <PR_NUMBER>`. Check whether `.github/PULL_REQUEST_TEMPLATE.md` exists in the repository root.
- Write `pr_body_new.md` with the Write tool.
- Ask the confirmation question with AskUserQuestion.

!`/bin/cat ~/.claude/common/pr_body_core.md`

!`/bin/cat ~/.claude/common/pr_body_format.md`
