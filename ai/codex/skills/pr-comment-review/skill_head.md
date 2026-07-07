---
name: pr-comment-review
description: >
  Analyze a GitHub PR comment/review comment URL. Use when the user asks Codex
  to investigate, explain, summarize, assess, or review a PR comment, including
  "PRコメントを確認して", "レビューコメントを分析して",
  "このコメントの意図を調べて", "analyze this PR comment", or `$pr-comment-review`.
---

## Inputs

```text
$pr-comment-review <PR_COMMENT_URL> [analysis instructions...]
```

- First token: `COMMENT_URL`; remaining text: `PROMPT`.
- Ask clarifications in plain text; never `request_user_input`.

### Core Analysis Rules
