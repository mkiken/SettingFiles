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

Parse `OWNER`, `REPO`, `PULL_NUMBER`, fragment type, and ID from
`https://github.com/{owner}/{repo}/pull/{pull_number}#...`.

- `#issuecomment-<id>`: standalone PR conversation comment.
- `#discussion_r<id>`: inline review comment.
- `#pullrequestreview-<id>`: pull request review summary and inline comments.

If no supported fragment exists, fetch the PR discussion and say no single target
comment could be identified.

Gather only the context needed for the parsed target:

```bash
# Baseline PR discussion
gh pr view "$COMMENT_URL" --comments
gh pr view "$PULL_NUMBER" --repo "$OWNER/$REPO" --comments

# Target comment or review
gh api "repos/${OWNER}/${REPO}/issues/comments/${COMMENT_ID}"
gh api "repos/${OWNER}/${REPO}/pulls/comments/${COMMENT_ID}"
gh api "repos/${OWNER}/${REPO}/pulls/${PULL_NUMBER}/reviews/${REVIEW_ID}"
gh api "repos/${OWNER}/${REPO}/pulls/${PULL_NUMBER}/reviews/${REVIEW_ID}/comments"

# Inline review thread reconstruction
gh api "repos/${OWNER}/${REPO}/pulls/${PULL_NUMBER}/comments"
```

- Use the parsed PR-number form if the URL form fails.
- For inline comments, reconstruct the root and replies from `in_reply_to_id`,
  then sort by `created_at`.
- For standalone comments, use the target plus baseline discussion.
- For `#pullrequestreview-<id>`, analyze the single inline comment if there is
  one; analyze the review as a group if there are multiple; analyze the summary
  if there are none. If `PROMPT` asks for one item among many, show candidates
  and ask which one.

If the comment references a path, line, symbol, behavior, or failing test, inspect
the current repo before concluding. If it points to stale code, locate the current
equivalent and state the evidence.

Do not change repository files.

## Output

Respond in Japanese. Focus on the URL target; related comments are context.

Use this structure:

```markdown
## 対象コメント
URL / 種別 / 投稿者 / 投稿日時 / 場所 / 内容

## 深掘り分析
意図 / 指摘内容 / 技術的根拠 / 妥当性

## 関連議論
同一スレッドまたは同一レビュー内の流れ / 対象コメントとの関係

## 推奨対応
優先度 / 具体的な対応 / 返信方針

## 補足
不明点 / 追加で確認すべき情報
```

If the comment is incorrect, too broad, stale, or already addressed, say so with
evidence. Do not invent certainty when repo or GitHub data is insufficient.
