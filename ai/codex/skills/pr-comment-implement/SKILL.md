---
name: pr-comment-implement
description: >
  Implement code changes requested by a GitHub Pull Request comment URL.
  Use this skill when the user provides a PR comment URL and asks Codex to
  fix, implement, address, respond to, or resolve the comment, including
  phrases such as "PRコメント対応", "このレビューコメントを直して",
  "implement this PR comment", or invokes `$pr-comment-implement`.
  The workflow performs analysis, presents an implementation design before
  editing, implements after approval, and can optionally commit, push, reply
  to the original comment, and resolve the review thread.
---

## Purpose

Implement a GitHub PR comment request without losing the reply target. Answer
review comments in their original thread when possible; never downgrade to a
standalone PR comment silently.

## Inputs

`$pr-comment-implement <PR_COMMENT_URL> [implementation instructions...]`

- First token: `PR_URL`; remainder: `PROMPT`.
- If `PR_URL` is missing or not a GitHub PR comment/review URL, ask for it in
  plain text.
- Use plain-text questions for all approvals and clarifications. Do not use
  `request_user_input`.

## Workflow

### Analysis

Before proposing changes:

```bash
gh pr view "$PR_URL" --comments
git status --short
```

Parse `PR_URL`, extracting `OWNER`, `REPO`, `PULL_NUMBER`, then classify:

- `#discussion_r<id>`: review comment thread; fetch with
  `gh api "repos/${OWNER}/${REPO}/pulls/comments/${COMMENT_ID}"`.
- `#pullrequestreview-<id>`: fetch review comments with
  `gh api "repos/${OWNER}/${REPO}/pulls/${PULL_NUMBER}/reviews/${REVIEW_ID}/comments" --jq '[.[] | {id,path,body:(.body | .[0:120])}]'`.
- `#issuecomment-<id>` or no fragment: standalone PR conversation comment;
  fetch issue comments as needed.

For `#pullrequestreview-<id>`:

- If exactly one inline comment exists, use it as the thread target.
- If multiple inline comments exist, show candidates and ask which to implement.
- If no inline comments exist, treat the review as standalone.

Read affected files and surrounding code. If the comment targets stale code,
inspect the current equivalent symbol or concept.

### Design Approval

Before editing, present this Japanese design and wait for explicit approval:

```markdown
## 実装設計

### 対応するコメント
- URL:
- 種別: review thread / review / standalone
- 要旨:

### 変更方針
- 変更する振る舞い:
- 変更しない範囲:

### 対象
- 変更予定ファイル:
- 追加予定ファイル:
- テスト更新:

### 影響
- 影響する呼び出し元:
- リスク:
- 確認方法:

この設計で実装を進めてよろしいですか？修正点があればお知らせください。
```

Revise and re-present if requested. Do not edit before approval.

### Implementation

After approval:

- Implement only the approved scope.
- Preserve unrelated user changes.
- Add or update tests when the change has behavioral risk.
- Run the narrowest useful verification command. Broaden only when the touched
  surface is shared or high risk.
- Review the final diff before preparing any GitHub action:

```bash
git diff --check
git diff
git status --short
```

### Prepare Commit, Reply, and Resolve Targets

Before asking what to execute, draft a commit message but do not commit. It
should reference the PR comment when useful, summarize the behavior change, and
follow the repository convention if present.

Determine `REPLY_PATH`:

- `thread`: use review comment reply API.
- `standalone`: use `gh pr comment`.

For thread replies, inspect the comment author and authenticated user:

```bash
META=$(gh api "repos/${OWNER}/${REPO}/pulls/comments/${COMMENT_ID}" \
  --jq '{login: .user.login, type: .user.type}')
COMMENT_AUTHOR=$(printf '%s\n' "$META" | jq -r '.login')
COMMENT_AUTHOR_TYPE=$(printf '%s\n' "$META" | jq -r '.type')
SELF_LOGIN=$(gh api user --jq '.login' 2>/dev/null || printf '')
```

`bot` means `COMMENT_AUTHOR_TYPE=Bot` or login ends with `[bot]`. `self` means
login matches `SELF_LOGIN`.

For `thread` replies from a bot or self, fetch the review thread node:

```bash
THREAD_JSON=$(gh api graphql \
  -F owner="$OWNER" -F name="$REPO" -F number="$PULL_NUMBER" \
  -f query='
    query($owner:String!,$name:String!,$number:Int!){
      repository(owner:$owner,name:$name){
        pullRequest(number:$number){
          reviewThreads(first:100){
            nodes{ id isResolved comments(first:50){ nodes{ databaseId } } }
          }
        }
      }
    }' \
  --jq "[.data.repository.pullRequest.reviewThreads.nodes[]
         | select(any(.comments.nodes[]; .databaseId == ${COMMENT_ID}))][0]")
```

Offer resolve only when `REPLY_PATH=thread`, the thread node exists, it is
unresolved, and the original author is bot or self.

Preview the reply with placeholder hashes until the commit exists:

```markdown
ご指摘ありがとうございます。対応しました。

- Commit: <created-after-commit>
  - <commit subject>
```

Then show:

```markdown
## 実装完了。以下を実行する準備ができました。

### コミットメッセージ（草案）
<draft commit message>

### Reply 宛先
- 方法: thread reply / standalone
- target: <comment_id or pull number>
- author: <login> (<type>, bot/self/other)

### Reply 本文プレビュー
<reply preview>

### Resolve 対象 thread
<thread id and unresolved status, or why resolve is not available>
```

### Unified Action Selection

Ask one plain-text final action question after the preview. Show only executable
options and renumber them:

```text
実装が完了しました。以下のうちどこまで自動実行しますか？

1. コミット & push & 返信 & resolve
2. コミット & push & 返信
3. コミット & push
4. コミットのみ
5. コミットしない
```

Hide the resolve option when unavailable and reply options when no reply target
exists. This is the commit decision for this workflow; do not ask the generic
post-implementation commit question again. If the user chooses
`コミットしない`, stop without git or GitHub side effects.

### Execute Selected Actions

Run only the selected actions and stop on failure unless the user chooses retry.

```bash
# Commit
PRE_COMMIT_HEAD=$(git rev-parse HEAD)
git status --short
git add <reviewed files>
git commit -m "<drafted message>"

# Push
git push origin HEAD

# Reply body
git log "${PRE_COMMIT_HEAD}..HEAD" --format='%H %s'

# Thread reply only
gh api "repos/${OWNER}/${REPO}/pulls/${PULL_NUMBER}/comments/${COMMENT_ID}/replies" \
  -X POST -f body="${BODY}"

# Standalone reply only
gh pr comment "${OWNER}/${REPO}#${PULL_NUMBER}" --body "${BODY}"
```

If push fails, ask whether to retry or stop; do not reply or resolve after a
failed push unless explicitly instructed. If thread reply fails, report the
error and ask whether to retry, downgrade to standalone, or stop; warn that
downgrading loses thread context. Never fallback automatically.

Run resolve only when selected:

```bash
gh api graphql \
  -F id="$THREAD_NODE_ID" \
  -f query='
    mutation($id:ID!){
      resolveReviewThread(input:{threadId:$id}){ thread{ id isResolved } }
    }'
```

If resolve fails or returns unresolved, ask whether to retry or skip.

## Final Summary

Report in Japanese:

- Modified files and behavior changes.
- Verification commands and results.
- Commit hash and message, if created.
- Push result, if executed.
- Reply URL or result, if posted.
- Resolve result, if executed.
- Remaining manual action, if any.
