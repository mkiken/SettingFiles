---
allowed-tools: Bash(gh:*)
description: "Analyzes PR review comments based on user instructions."
argument-hint: [prCommentUrl] [instructions...]
effort: max
---

## Instructions

- Treat the first `$ARGUMENTS` token as `COMMENT_URL`; the rest is `PROMPT`.

### Step 1: Parse the Comment URL

- From `https://github.com/{owner}/{repo}/pull/{pull_number}#...`, extract `owner`, `repo`, `pull_number`, comment type, and ID.
- `#issuecomment-{id}` = Issue Comment; `#discussion_r{id}` = Review Comment.

### Step 2: Fetch the Target Comment

- Issue Comment:
  ```bash
  gh api repos/{owner}/{repo}/issues/comments/{comment_id}
  ```
- Review Comment:
  ```bash
  gh api repos/{owner}/{repo}/pulls/comments/{comment_id}
  ```

### Step 3: Fetch Thread Context

For Review Comment, fetch all PR review comments and reconstruct the target thread with `in_reply_to_id`:

```bash
gh api repos/{owner}/{repo}/pulls/{pull_number}/comments
```

For Issue Comment, treat the target as standalone.

### Step 4: Focused Analysis

- Analyze the URL's **target comment** first; use related comments only as context.
- Output detailed Japanese analysis in this structure.

---

### **Target Comment Details**

- **Author**:
- **Posted at**:
- **Location**: file path/line, if any
- **Content**:

### **Deep Analysis**

Based on `$PROMPT`, cover:

- Intent and purpose
- Pointed-out issues
- Technical background and reasoning
- Recommended response

### **Related Discussion**

- Same-thread discussion flow
- Relationship to the target comment

### **Recommended Actions**

- Specific actions
- Priority and direction

### **Additional Notes**

- Other important information
