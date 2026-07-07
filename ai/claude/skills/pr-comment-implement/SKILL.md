---
allowed-tools: Bash(gh:*), Bash(/bin/cat:*), Read, Edit, Write, Bash(git:*)
description: "Implement code changes based on PR review comments, with design review phase before implementation."
argument-hint: [prCommentUrl] [instructions...]
disable-model-invocation: true
effort: max
---

## Instructions

- First `$ARGUMENTS` token is `PR_URL`; the rest is `PROMPT`.
- Fetch context with `gh pr view "$PR_URL" --comments`; it resolves the PR from
  the comment URL.
- Use `AskUserQuestion` for approvals, target selection, retries, and the final
  action selection. Treat Other or cancel on the final action question as
  "no action" (equivalent to `コミットしない`).
- In plan mode, the plan artifact is the plan file.

## Core Workflow

!`/bin/cat ~/.claude/common/pr_comment_implement_core.md`
