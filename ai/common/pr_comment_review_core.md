- From `COMMENT_URL` (`https://github.com/{owner}/{repo}/pull/{pull_number}#...`), extract `owner`, `repo`, `pull_number`, comment type, and ID:
  `#issuecomment-{id}` = Issue Comment; `#discussion_r{id}` = Review Comment; `#pullrequestreview-{id}` = Pull Request Review (summary + inline comments).

```bash
gh api repos/{owner}/{repo}/issues/comments/{comment_id}
gh api repos/{owner}/{repo}/pulls/comments/{comment_id}
gh api repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}
gh api repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/comments
gh api repos/{owner}/{repo}/pulls/{pull_number}/comments --paginate
```

- Run only the API calls matching the parsed target.
- Review Comment: read the full thread, not just the URL comment. Set
  `ROOT_COMMENT_ID` to `in_reply_to_id` if present, else the target `id`; filter
  all PR review comments to the root plus replies, sorted by `created_at`.
- Pull Request Review: analyze the single inline comment if there is one
  (reading its full thread as above before concluding); the review as a group
  if multiple; the summary if none.
- Issue Comment: treat as standalone.
- Analyze the URL target first, using related comments as context; fold
  same-thread corrections, constraints, or implementation intent into the
  analysis and recommendation.
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
