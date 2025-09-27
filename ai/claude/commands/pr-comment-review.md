---
allowed-tools: Bash(gh:*)
description: "Analyzes PR review comments based on user instructions."
model: claude-opus-4-1
argument-hint: [prCommentUrl] [instructions...]
---
ultrathink

## Instructions
- Interpret the first argument from `$ARGUMENTS` as the PR comment URL (`$PR_URL`) and the rest as user instructions (`$PROMPT`).
- Use `gh pr view $PR_URL --comments` to fetch and analyze the review comments. The `gh` command automatically resolves the PR from the comment URL.
- Analyze the review comments based on the user's instructions in `$PROMPT`.
- Output a detailed analysis in Japanese using the following structure.

### **Review Comment Summary**
- Summarize the overall trend of comments, key points, and discussion status.

### **Key Points of Discussion**
- Identify and list important points based on the `$PROMPT`.
- For each point, clarify the following:
  - **Author**: The user who commented.
  - **Comment**: A summary of the comment.
  - **Location**: The part of the code being discussed.
  - **Priority**: (High/Medium/Low)

### **Points of Contention**
- Identify areas with differing opinions or active debate.
- For each point, organize and present the different views and proposals.

### **Recommended Actions**
- Based on the analysis, suggest the next steps for the PR author and reviewers.
- (e.g., address specific feedback, provide additional clarification, schedule a meeting).

### **Additional Notes**
- Include any other important information to share.

- **Output to file**: Ask the user if they want to save the generated review. If yes, save it to `/tmp/pr-comment-review-$(basename "$PR_URL" | cut -d'#' -f1 | sed 's|.*/||').md`.