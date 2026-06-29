---
allowed-tools: Bash(gh:*)
description: "Analyzes PR review comments based on user instructions."
argument-hint: [prCommentUrl] [instructions...]
effort: max
---

## Instructions

- Treat the first `$ARGUMENTS` token as `COMMENT_URL`; the rest is `PROMPT`.
- From `https://github.com/{owner}/{repo}/pull/{pull_number}#...`, extract `owner`, `repo`, `pull_number`, comment type, and ID.
- `#issuecomment-{id}` = Issue Comment; `#discussion_r{id}` = Review Comment.

```bash
gh api repos/{owner}/{repo}/issues/comments/{comment_id}
gh api repos/{owner}/{repo}/pulls/comments/{comment_id}
gh api repos/{owner}/{repo}/pulls/{pull_number}/comments
```

- Run only the API calls matching the parsed target.
- For Review Comment, reconstruct the target thread with `in_reply_to_id`.
- For Issue Comment, treat the target as standalone.
- Analyze the URL target first, using related comments only as context.
- Respond in Japanese using this structure:

### **Target Comment Details**
Author / Posted at / Location / Content

### **Deep Analysis**
Intent / pointed-out issues / technical reasoning / recommended response

### **Related Discussion**
Same-thread discussion flow / relationship to the target comment

### **Recommended Actions**
Specific actions / priority and direction

### **Additional Notes**
Other important information
