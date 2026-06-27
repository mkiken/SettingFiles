---
name: pr-comment-review
description: >
  Analyze a GitHub PR comment/review comment URL. Use when the user asks Codex
  to investigate, explain, summarize, assess, or review a PR comment, including
  "PRコメントを確認して", "レビューコメントを分析して",
  "このコメントの意図を調べて", "analyze this PR comment", or `$pr-comment-review`.
---

## Purpose

Read-only analysis of one GitHub PR comment plus enough context to explain its
intent, technical basis, and recommended response. Do not edit files, post
comments, resolve threads, commit, or push.

## Inputs

```text
$pr-comment-review <PR_COMMENT_URL> [analysis instructions...]
```

- First token: `COMMENT_URL`; remaining text: `PROMPT`.
- If missing or not a GitHub PR comment/review URL, ask for the URL in plain text.
- Use plain-text clarification questions; do not use `request_user_input`.

## Workflow

### Parse the URL

Extract `OWNER`, `REPO`, and `PULL_NUMBER` from:

```text
https://github.com/{owner}/{repo}/pull/{pull_number}#...
```

Classify the fragment:

- `#issuecomment-<id>`: standalone PR conversation comment.
- `#discussion_r<id>`: inline review comment.
- `#pullrequestreview-<id>`: pull request review summary and its inline comments.

If no supported fragment exists, fetch the PR discussion and say no single target
comment could be identified.

### Fetch Baseline PR Context

Gather visible PR discussion first:

```bash
gh pr view "$COMMENT_URL" --comments
```

If the URL cannot be resolved, use the parsed values:

```bash
gh pr view "$PULL_NUMBER" --repo "$OWNER/$REPO" --comments
```

### Fetch the Target

Use the API matching the fragment:

```bash
# Standalone PR conversation comment
gh api "repos/${OWNER}/${REPO}/issues/comments/${COMMENT_ID}"

# Inline review comment
gh api "repos/${OWNER}/${REPO}/pulls/comments/${COMMENT_ID}"

# Pull request review summary
gh api "repos/${OWNER}/${REPO}/pulls/${PULL_NUMBER}/reviews/${REVIEW_ID}"
gh api "repos/${OWNER}/${REPO}/pulls/${PULL_NUMBER}/reviews/${REVIEW_ID}/comments"
```

For `#pullrequestreview-<id>`: with one inline comment, analyze it and use the
summary as context; with multiple, analyze the review as a group unless `PROMPT`
asks for one item, then show candidates and ask; with none, analyze the summary.

### Fetch Thread Context

For an inline review comment, fetch all inline PR comments:

```bash
gh api "repos/${OWNER}/${REPO}/pulls/${PULL_NUMBER}/comments"
```

Reconstruct the target thread:

- Root is the target if it has no `in_reply_to_id`; otherwise root is the comment
  whose `id` equals `in_reply_to_id`.
- Thread replies are comments whose `in_reply_to_id` equals the root comment ID.
- Sort the root and replies by `created_at`.

For standalone PR conversation comments, treat the target as standalone and use
the baseline discussion only as context.

### Inspect Code When Needed

If the comment references a path, line, symbol, behavior, or failing test, inspect
the current repo before concluding. If it points to stale code, locate the current
equivalent and state the evidence.

Do not change repository files.

## Output

Respond in Japanese. Focus on the URL target; related comments are context.

Use this structure:

```markdown
## 対象コメント

- URL:
- 種別: issue comment / review comment / pull request review
- 投稿者:
- 投稿日時:
- 場所: path:line, review summary, or PR conversation
- 内容:

## 深掘り分析

- 意図:
- 指摘内容:
- 技術的根拠:
- 妥当性:

## 関連議論

- 同一スレッドまたは同一レビュー内の流れ:
- 対象コメントとの関係:

## 推奨対応

- 優先度:
- 具体的な対応:
- 返信方針:

## 補足

- 不明点:
- 追加で確認すべき情報:
```

If the comment is incorrect, too broad, stale, or already addressed, say so with
evidence. Do not invent certainty when repo or GitHub data is insufficient.
