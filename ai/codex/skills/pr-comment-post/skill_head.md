---
name: pr-comment-post
description: >
  Post specific findings from pr-review results as GitHub PR inline comments.
  Use this skill when the user wants to post review findings to a GitHub PR,
  comment on a PR with specific numbered review items, or push review results to GitHub
  as inline code comments. Trigger whenever the user says things like "PRにコメントして",
  "レビュー結果を投稿して", "番号を指定してコメント", "GitHubにコメント" after running
  a PR review with pr-review skill. Accepts space- or comma-separated item numbers
  (e.g., "1 3 5" or "1,3,5").
---

## Instructions

- `ITEM_NUMBERS` = the item numbers in the user's message.
- `{ai_header}` = `🤖 **Codex Review**`.
