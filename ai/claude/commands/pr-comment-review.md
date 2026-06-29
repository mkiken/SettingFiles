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
- `#pullrequestreview-{id}` = Pull Request Review summary and inline comments.

```bash
gh api repos/{owner}/{repo}/issues/comments/{comment_id}
gh api repos/{owner}/{repo}/pulls/comments/{comment_id}
gh api repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}
gh api repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/comments
gh api repos/{owner}/{repo}/pulls/{pull_number}/comments --paginate
```

- Run only the API calls matching the parsed target.
- For Review Comment, always read the complete target thread, not only the URL
  comment. Fetch the target comment, set `ROOT_COMMENT_ID` to `in_reply_to_id`
  when present or the target `id` otherwise, then filter all PR review comments
  to the root plus replies and sort them by `created_at`.
- For Pull Request Review, analyze the single inline comment if there is one;
  analyze the review as a group if there are multiple; analyze the summary if
  there are none. When a concrete inline comment is selected, reconstruct and
  read that comment's complete review thread before concluding.
- For Issue Comment, treat the target as standalone.
- Analyze the URL target first, using related comments only as context.
- If same-thread comments add corrections, constraints, or implementation
  intent, include that information in the analysis and recommendation.
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
