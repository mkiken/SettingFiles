---
name: pr-comment-post
description: >
  Post specific findings from my:pr-review results as GitHub PR inline comments.
  Use this skill when the user wants to post Claude's review findings to a GitHub PR,
  comment on a PR with specific numbered review items, or push review results to GitHub
  as inline code comments. Trigger whenever the user says things like "PRにコメントして",
  "レビュー結果を投稿して", "番号を指定してコメント", "GitHubにコメント" after running
  a PR review with my:pr-review or pr-review-subagents. Always use this skill when the
  user wants to post specific numbered items from a Claude review to GitHub.
model: sonnet
allowed-tools: Bash(gh:*), Bash(git:*), Bash(/bin/cat:*)
argument-hint: "[item_numbers...]"
disable-model-invocation: true
---

## Instructions

- `ITEM_NUMBERS` = `$ARGUMENTS`.
- `pr-review` in the core workflow refers to the `my:pr-review` output.
- `{ai_header}` = `🤖 **Claude Code Review**`.
- For every user confirmation, use `AskUserQuestion`.

## Core Workflow

!`/bin/cat ~/.claude/common/pr_comment_post_core.md`
