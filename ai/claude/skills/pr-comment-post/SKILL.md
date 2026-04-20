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
disable-model-invocation: true
---

## Purpose

Post specific numbered findings from a `my:pr-review` result as a single GitHub Pull Request Review.
All items are confirmed together before posting, then submitted in one API call.

## Step 1: Summarize review items

Before anything else, look at the conversation history for `my:pr-review` output and list all findings in a compact format — one line per item:

```
N. [path/to/file.ext:line] Priority | Category: 概要
```

Example:

```
1. [src/auth.ts:42] 🔴 High | Security: トークンがログに露出する可能性
2. [src/Button.tsx:15-20] 🟡 Medium | Architecture: ロジックの分離を検討
3. [src/utils/format.ts:8] 🟢 Low | Readability: 変数名をより具体的に
```

## Step 2: Determine which item numbers to post

Parse `$ARGUMENTS` for space- or comma-separated numbers (e.g., `1 3 5` or `1,3,5`).

If `$ARGUMENTS` is empty, use `AskUserQuestion` to ask the user which item numbers to post.
Show them the available numbered items from the review output in context.

## Step 3: Extract review items from context

Look at the conversation history for `my:pr-review` output. For each requested number N, extract:

- **file_path**: e.g., `src/services/auth.ts`
- **line_spec**: e.g., `42` (single) or `15-20` (range)
- **priority**: `High`, `Medium`, or `Low` (from the section heading 🔴/🟡/🟢)
- **category**: e.g., `Security`, `Architecture`, `Bug Risk`
- **description**: the full issue description text

Map priority to emoji:

- High → `🔴`
- Medium → `🟡`
- Low → `🟢`

## Step 4: Get PR metadata

Run these commands to collect what you need for posting:

```bash
# Get PR number and head commit SHA
gh pr view --json number,headRefOid

# Get repo owner and name
gh repo view --json owner,name
```

## Step 5: Show all items and confirm in bulk

### 5a. Display all items to be posted

Present all items clearly:

```
投稿予定のレビューコメント一覧:

1. [src/auth.ts:42] 🔴 High | Security: トークンがログに露出する可能性
2. [src/Button.tsx:15-20] 🟡 Medium | Architecture: ロジックの分離を検討
3. [src/utils/format.ts:8] 🟢 Low | Readability: 変数名をより具体的に
```

### 5b. Ask for bulk confirmation

Use `AskUserQuestion` to ask:

> 上記 N 件をまとめて Pull Request Review として投稿しますか？
> 除外したい項目があれば番号を指定してください（例: 2,3 を除外）。

If the user specifies items to exclude, remove them from the posting list and confirm the final list.

### 5c. Generate summary for review body

Before posting, generate a concise summary of all items being posted. This will be the top-level review body that appears once. The summary should:

- Mention the general areas of concern (e.g., security, test coverage)
- NOT include specific file names or line numbers (those are in the inline comments)
- Be 1-3 sentences in Japanese

Example:

```
セキュリティに関する指摘が1件、アーキテクチャに関する指摘が1件、可読性に関する指摘が1件あります。認証トークンの取り扱いとコンポーネント設計の改善について検討をお願いします。
```

### 5d. Post as Pull Request Review

Build the comments JSON and post using the Review API. Capture stdout and stderr together to inspect the exit code and error message afterwards:

```bash
# Build the full JSON body with jq and pipe directly to gh api (no temp file needed).
# Each comment body format: {emoji} **{Priority}** / **{Category}**: {Description}
# For single-line items: include "line" only.
# For multi-line ranges (e.g., 15-20): include both "start_line" (start) and "line" (end).

api_response=$(jq -n \
  --arg body "🤖 **Claude Code Review**

{summary}" \
  --arg event "COMMENT" \
  --arg commit_id "{head_sha}" \
  --argjson comments '[
    {"path": "path/to/file.ext", "line": 42, "body": "🔴 **High** / **Security**: Description"},
    {"path": "path/to/file2.ext", "line": 20, "start_line": 15, "body": "🟡 **Medium** / **Architecture**: Description"}
  ]' \
  '{body: $body, event: $event, commit_id: $commit_id, comments: $comments}' \
| gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews --input - 2>&1)
api_exit_code=$?
```

**If the command succeeds** (`api_exit_code == 0`), proceed to Step 6.

**If the command fails** (`api_exit_code != 0`):
- Check whether `$api_response` contains `"one pending review"` or `"pending review per pull request"`.
  - **Yes** → PENDING conflict detected → go to **Step 5f**.
  - **No** → Other error → go to **Step 5e** (individual comment fallback).

### Inline comment body format

Each inline comment uses this format — no AI header, no item numbers:

```markdown
{priority_emoji} **{Priority}** / **{Category}**: {Description}
```

Examples:

```markdown
🔴 **High** / **Security**: Auth token may be exposed in logs — consider using a redaction helper before passing to the logger.
```

```markdown
🟢 **Low** / **Test Coverage**: GetMissionClearedCounts メソッドに対する単体テストが含まれていないように見受けられます。エッジケースを含めたテストを追加することを推奨します。
```

### 5e. Fallback if Review API fails (non-PENDING errors only)

> **Note:** If the error contains `"one pending review"` or `"pending review per pull request"`, use **Step 5f** instead. This fallback is for all other API errors.

If the Review API call fails, fall back to posting each comment individually:

```bash
gh api repos/{owner}/{repo}/pulls/{pr_number}/comments \
  -f body="{comment_body_with_header}" \
  -f commit_id="{head_sha}" \
  -f path="{file_path}" \
  -F line={end_line} \
  -f side="RIGHT"
```

In fallback mode, prefix each comment body with the AI header:

```markdown
> 🤖 **Claude Code Review**

{priority_emoji} **{Priority}** / **{Category}**: {Description}
```

For multi-line ranges, also include:

```bash
  -F start_line={start_line} \
  -f start_side="RIGHT"
```

**For general PR comments (fallback when file/line is not available):**

```bash
gh pr comment {pr_number} --body "{comment_body}"
```

### 5f. Handle PENDING review conflict

A PENDING review (draft review not yet submitted) already exists for this pull request. The Review API rejected the request because only one PENDING review is allowed per user per PR.

Retrieve the PENDING review ID:

```bash
viewer=$(gh api user --jq .login)
pending_id=$(gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews \
  --jq ".[] | select(.state==\"PENDING\" and .user.login==\"$viewer\") | .id" | head -1)
```

Use `AskUserQuestion` to present the following choice:

> GitHub に未 submit のレビュー (PENDING) が残っているため投稿に失敗しました。
> 対処方法を選んでください:
>
> - **submit して続行** — 既存の PENDING レビューを COMMENT として submit した後、今回のコメントを新たな Review として投稿します。
> - **中断** — 何もしません。GitHub UI の「Files changed」タブで PENDING レビューを Submit または Cancel してから再実行してください。

**If the user chooses "submit して続行":**

```bash
# Submit the existing PENDING review
gh api --method POST repos/{owner}/{repo}/pulls/{pr_number}/reviews/$pending_id/events \
  -f event=COMMENT

# Retry Step 5d exactly once
api_response=$(jq -n ... | gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews --input - 2>&1)
api_exit_code=$?
```

If the retry succeeds, proceed to Step 6.
If the retry also fails, **do not retry again** — report the error and abort.

**If the user chooses "中断":**

Proceed directly to Step 6 and report that posting was aborted due to a PENDING review conflict.

---

## Step 6: Summary

After posting, report:

- How many comments were posted as a review
- Which path was taken:
  - Review API での一括投稿に成功
  - PENDING レビューを submit してから再投稿に成功
  - 5e の個別コメント fallback に切り替えて投稿
  - PENDING 競合のため中断
- How many items were skipped (if any)

---

## Notes

- Use the Pull Request Review API to post all comments in a single review.
- The AI header (`🤖 **Claude Code Review**`) appears only once in the review body, not in each inline comment.
- Inline comments contain only priority emoji, priority level, category, and description — no numbers, no headers.
- If `gh pr view` fails (not in a git repo, or no PR for current branch), ask the user to provide the PR number manually.
- The `gh api` inline comment endpoint requires a valid `commit_id`. If the commit SHA cannot be retrieved, fall back to `gh pr comment`.
