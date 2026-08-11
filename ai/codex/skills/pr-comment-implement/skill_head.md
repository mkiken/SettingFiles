---
name: pr-comment-implement
description: >
  Implement code changes requested by a GitHub Pull Request comment URL.
  Use this skill when the user provides a PR comment URL and asks Codex to
  fix, implement, address, respond to, or resolve the comment, including
  phrases such as "PRコメント対応", "このレビューコメントを直して",
  "implement this PR comment", or invokes `$pr-comment-implement`.
  The workflow performs analysis, presents an implementation design before
  editing, implements after approval, and can optionally commit, merge, push,
  reply to the original comment, and resolve the review thread.
---

## Inputs

```text
$pr-comment-implement <PR_COMMENT_URL> [implementation instructions...]
```

- First token: `PR_URL`; remaining text: `PROMPT`.
- On the final action question, offer an explicit `コミットしない` choice.
- In Plan Mode, the plan artifact is the `<proposed_plan>` block.

## Core Workflow
