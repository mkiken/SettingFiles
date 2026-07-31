---
allowed-tools: Bash(gh:*), Bash(/bin/cat:*)
description: "Analyzes PR review comments based on user instructions."
argument-hint: [prCommentUrl] [instructions...]
disable-model-invocation: true
effort: high
---

## Instructions

- Treat the first `$ARGUMENTS` token as `COMMENT_URL`; the rest is `PROMPT`.

### Core Analysis Rules

!`/bin/cat ~/.claude/common/pr_comment_review_core.md`
