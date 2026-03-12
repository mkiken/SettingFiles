---
name: pr-comment-post
description: >
  Post specific findings from my:pr-review results as GitHub PR inline comments.
  Use this skill when the user wants to post Claude's review findings to a GitHub PR,
  comment on a PR with specific numbered review items, or push review results to GitHub
  as inline code comments. Trigger whenever the user says things like "PRにコメントして",
  "レビュー結果を投稿して", "番号を指定してコメント", "GitHubにコメント" after running
  a PR review with my:pr-review or pr-review-subagents. Always use this skill when the
  user wants to post specific numbered items from a Claude review to GitHub.
model: sonnet
allowed-tools: Bash(gh:*), Bash(git:*)
argument-hint: "[item_numbers...]"
---

## Purpose

Post specific numbered findings from a `my:pr-review` result as GitHub PR comments.
Each item is confirmed with the user individually before posting.

## Step 1: Determine which item numbers to post

Parse `$ARGUMENTS` for space- or comma-separated numbers (e.g., `1 3 5` or `1,3,5`).

If `$ARGUMENTS` is empty, use `AskUserQuestion` to ask the user which item numbers to post.
Show them the available numbered items from the review output in context.

## Step 2: Extract review items from context

Look at the conversation history for `my:pr-review` output. The format is:

```
N. **[path/to/file.ext:line]** Category: Description
```

For each requested number N, extract:
- **file_path**: e.g., `src/services/auth.ts`
- **line_spec**: e.g., `42` (single) or `15-20` (range)
- **category**: e.g., `Security`, `Architecture`, `Bug Risk`
- **description**: the full issue description text

## Step 3: Get PR metadata

Run these commands to collect what you need for posting:

```bash
# Get PR number and head commit SHA
gh pr view --json number,headRefOid

# Get repo owner and name
gh repo view --json owner,name
```

## Step 4: Confirm and post each item

For each item number the user specified, repeat this loop:

### 4a. Show what will be posted

Present the item clearly to the user:

```
項目 N:
  ファイル: path/to/file.ext (行: 42)
  内容:
    **Category**: Description
```

### 4b. Ask for confirmation

Use `AskUserQuestion` with a yes/no question like:

> この項目をPRにコメントとして投稿しますか？

### 4c. Post if approved

If the user approves, post the comment.

**For inline comments (file path and line number available):**

```bash
gh api repos/{owner}/{repo}/pulls/{pr_number}/comments \
  -f body="{comment_body}" \
  -f commit_id="{head_sha}" \
  -f path="{file_path}" \
  -F line={end_line} \
  -f side="RIGHT"
```

For multi-line ranges (e.g., `15-20`), also include:
```bash
  -F start_line={start_line} \
  -f start_side="RIGHT"
```

**For general PR comments (fallback when file/line is not available):**

```bash
gh pr comment {pr_number} --body "{comment_body}"
```

### Comment body format

Always use this format so it's clear the comment comes from Claude:

```markdown
> 🤖 **Claude Code Review**

**{Category}**: {Description}
```

Example:
```markdown
> 🤖 **Claude Code Review**

**Security**: Auth token may be exposed in logs — consider using a redaction helper before passing to the logger.
```

### 4d. Skip if declined

If the user says no, move on to the next item without posting.

## Step 5: Summary

After processing all items, report how many comments were posted and how many were skipped.

---

## Notes

- Never post multiple items at once without per-item confirmation.
- Always identify yourself as Claude in the comment body using the header above.
- If `gh pr view` fails (not in a git repo, or no PR for current branch), ask the user to provide the PR number manually.
- The `gh api` inline comment endpoint requires a valid `commit_id`. If the commit SHA cannot be retrieved, fall back to `gh pr comment`.
