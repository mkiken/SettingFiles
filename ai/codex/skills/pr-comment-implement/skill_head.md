---
name: pr-comment-implement
description: >
  Implement changes requested by a GitHub PR comment URL. Use for a specific
  review comment; the workflow can reply to and resolve its thread.
---

## Inputs

```text
$pr-comment-implement <PR_COMMENT_URL> [implementation instructions...]
```

- First token: `PR_URL`; remaining text: `PROMPT`.
- On the final action question, offer an explicit `コミットしない` choice.
- In Plan Mode, the plan artifact is the `<proposed_plan>` block.

## Core Workflow
