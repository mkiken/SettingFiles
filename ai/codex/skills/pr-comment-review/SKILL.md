---
name: pr-comment-review
description: >
  Analyze a specific GitHub Pull Request comment or review comment from its URL.
  Use this skill when the user provides a PR comment URL and asks Codex to
  investigate, explain, summarize, assess, or review the comment, including
  phrases such as "PRコメントを確認して", "レビューコメントを分析して",
  "このコメントの意図を調べて", "analyze this PR comment", or invokes
  `$pr-comment-review`.
---

## Purpose

Analyze one GitHub PR comment with enough surrounding discussion to explain the
comment's intent, technical basis, and recommended response. This skill is
read-only: do not edit files, post GitHub comments, resolve threads, commit, or
push.

## Inputs

Interpret the user's message as:

```text
$pr-comment-review <PR_COMMENT_URL> [analysis instructions...]
```

- The first token is `COMMENT_URL`.
- The remaining text is `PROMPT`.
- If `COMMENT_URL` is missing or is not a GitHub PR comment/review URL, ask the
  user for the URL in plain text.
- Use plain-text questions for every clarification. Do not use
  `request_user_input`.

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

If the URL has no supported fragment, fetch the PR discussion and explain that no
single target comment could be identified.

### Fetch Baseline PR Context

Gather the visible PR discussion first:

```bash
gh pr view "$COMMENT_URL" --comments
```

If this fails because the URL cannot be resolved, parse `OWNER`, `REPO`, and
`PULL_NUMBER` manually and use:

```bash
gh pr view "$PULL_NUMBER" --repo "$OWNER/$REPO" --comments
```

### Fetch the Target

Use the appropriate API for the parsed fragment:

```bash
# Standalone PR conversation comment
gh api "repos/${OWNER}/${REPO}/issues/comments/${COMMENT_ID}"

# Inline review comment
gh api "repos/${OWNER}/${REPO}/pulls/comments/${COMMENT_ID}"

# Pull request review summary
gh api "repos/${OWNER}/${REPO}/pulls/${PULL_NUMBER}/reviews/${REVIEW_ID}"
gh api "repos/${OWNER}/${REPO}/pulls/${PULL_NUMBER}/reviews/${REVIEW_ID}/comments"
```

For a pull request review URL:

- If the review has one inline comment, analyze that comment as the concrete
  target and treat the review summary as context.
- If the review has multiple inline comments, analyze the review as a group
  unless `PROMPT` asks about one specific item. When a single item is required,
  show the concrete candidates and ask the user which one to analyze.
- If the review has no inline comments, analyze the review summary as the target.

### Fetch Thread Context

For an inline review comment, fetch all inline PR comments:

```bash
gh api "repos/${OWNER}/${REPO}/pulls/${PULL_NUMBER}/comments"
```

Reconstruct the target thread:

- The root comment is the target comment itself when it has no
  `in_reply_to_id`.
- The root comment is the comment whose `id` equals `in_reply_to_id` when the
  target is a reply.
- Thread replies are comments whose `in_reply_to_id` equals the root comment ID.
- Sort the root and replies by `created_at`.

For a standalone PR conversation comment, treat the target as standalone and use
the baseline PR discussion only as supplementary context.

### Inspect Code When Needed

If the comment references a path, line, symbol, behavior, or failing test, inspect
the current repository state before drawing conclusions. If the comment points to
stale code, locate the current equivalent symbol or concept and state the
evidence.

Do not change repository files.

## Output

Respond in Japanese. Focus on the target comment specified by the URL; related
comments are context, not the main subject.

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

If the comment is incorrect, too broad, stale, or already addressed, say so
directly and explain the evidence. Do not invent certainty when the repository or
GitHub data is insufficient.
