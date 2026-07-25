---
name: pr-comment-post
description: >
  Post selected numbered findings from a pr-review or pr-review-subagents result
  as GitHub PR inline comments.
model: sonnet
allowed-tools: Bash(gh:*), Bash(git:*), Bash(jq:*), Bash(/bin/cat:*)
argument-hint: "[item_numbers...]"
disable-model-invocation: true
---

## Instructions

- `ITEM_NUMBERS` = `$ARGUMENTS`.
- `pr-review` in the core workflow refers to the `/pr-review` or `/pr-review-subagents` skill output.
- `{ai_header}` = `🤖 **Claude Code Review**`.
- For every user confirmation, use `AskUserQuestion`.

## Core Workflow

!`/bin/cat ~/.claude/common/pr_comment_post_core.md`
!`/bin/cat ~/.claude/common/pr_post_mechanics_core.md`
