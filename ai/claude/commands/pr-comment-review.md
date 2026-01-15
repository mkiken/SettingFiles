---
allowed-tools: Bash(gh pr view *), Bash(gh api *)
description: "Analyzes PR review comments based on user instructions."
argument-hint: [prCommentUrl] [instructions...]
---
ultrathink

## Instructions
- Interpret the first argument from `$ARGUMENTS` as the PR comment URL (`$COMMENT_URL`) and the rest as user instructions (`$PROMPT`).

### Step 1: Parse the Comment URL
- Extract the comment type and ID from `$COMMENT_URL`:
  - If URL contains `#issuecomment-{id}` → Issue Comment (comment on PR as a whole)
  - If URL contains `#discussion_r{id}` → Review Comment (comment on code lines)
- Extract `owner`, `repo`, and `pull_number` from the URL path (format: `https://github.com/{owner}/{repo}/pull/{pull_number}#...`).

### Step 2: Fetch the Target Comment
- For Issue Comment:
  ```bash
  gh api repos/{owner}/{repo}/issues/comments/{comment_id}
  ```
- For Review Comment:
  ```bash
  gh api repos/{owner}/{repo}/pulls/comments/{comment_id}
  ```

### Step 3: Fetch Thread Context
- For Review Comment, fetch full review thread:
  ```bash
  gh api repos/{owner}/{repo}/pulls/{pull_number}/comments
  ```
  Filter by `in_reply_to_id` to reconstruct thread containing target comment.

- For Issue Comment, target is typically standalone.

### Step 4: Focused Analysis
- Analyze primarily based on the **target comment** specified by the URL.
- Use related comments only as supplementary context.
- Output a detailed analysis in Japanese using the following structure.

---

### **Target Comment Details**
- **Author**: Comment author
- **Posted at**: Timestamp
- **Location**: Code location (for Review Comment: file path, line number)
- **Content**: Full comment text

### **Deep Analysis**
Based on `$PROMPT`, provide in-depth analysis of the target comment:
- Intent and purpose of the comment
- Detailed issues pointed out
- Technical background and reasoning
- Recommended response methods

### **Related Discussion**
- If there are comments in the same thread, summarize the discussion flow
- Clarify relationship to the target comment

### **Recommended Actions**
- Specific actions based on the target comment
- Priority and direction

### **Additional Notes**
- Other important information
