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

Implement the requested change from a specific GitHub PR comment while keeping
the reply target precise. Review comments must be answered in their original
thread when possible; do not silently downgrade them to standalone PR comments.

## Inputs

Interpret the user's message as:

```text
$pr-comment-implement <PR_COMMENT_URL> [implementation instructions...]
```

- The first token is `PR_URL`.
- The remaining text is `PROMPT`.
- If `PR_URL` is missing or is not a GitHub PR comment/review URL, ask the user
  for the URL in plain text.

Use plain-text questions for every approval or clarification. Do not use
`request_user_input`.

## Workflow

### Analysis

Gather enough context before proposing changes:

```bash
gh pr view "$PR_URL" --comments
git status --short
```

Parse `PR_URL`:

- Extract `OWNER`, `REPO`, and `PULL_NUMBER` from
  `https://github.com/{owner}/{repo}/pull/{pull_number}`.
- Classify the fragment:
  - `#discussion_r<id>`: target is a review comment thread.
  - `#pullrequestreview-<id>`: target is a pull request review; resolve the
    concrete inline comment if possible.
  - `#issuecomment-<id>` or no fragment: target is a standalone PR conversation
    comment.

Fetch the target comment:

```bash
# Standalone issue comment
gh api "repos/${OWNER}/${REPO}/issues/comments/${COMMENT_ID}"

# Review comment
gh api "repos/${OWNER}/${REPO}/pulls/comments/${COMMENT_ID}"

# Comments attached to a pull request review
gh api "repos/${OWNER}/${REPO}/pulls/${PULL_NUMBER}/reviews/${REVIEW_ID}/comments" \
  --jq '[.[] | {id: .id, path: .path, body: (.body | .[0:120])}]'
```

For `#pullrequestreview-<id>`:

- If exactly one inline comment exists, use it as the thread target.
- If multiple inline comments exist, show the concrete candidates and ask the
  user which one to implement.
- If no inline comments exist, treat the review as standalone.

Read the affected files and surrounding code before designing the change. If the
comment points to stale code, inspect the current equivalent symbol or concept.

### Design Approval

Before editing, present the design in Japanese and wait for explicit approval.

Use this structure:

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

If the user requests changes to the design, revise and present it again. Do not
edit files until the user approves.

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

Resolve all information needed for the final action selection before asking the
user what to execute.

Draft a commit message that:

- References the PR comment when useful.
- Summarizes the behavior change.
- Follows the repository's commit convention if one exists.

Do not commit yet.

Determine the reply path:

- `thread`: use the review comment reply API.
- `standalone`: use `gh pr comment`.

For thread replies, inspect the comment author and authenticated user:

```bash
META=$(gh api "repos/${OWNER}/${REPO}/pulls/comments/${COMMENT_ID}" \
  --jq '{login: .user.login, type: .user.type}')
COMMENT_AUTHOR=$(printf '%s\n' "$META" | jq -r '.login')
COMMENT_AUTHOR_TYPE=$(printf '%s\n' "$META" | jq -r '.type')
SELF_LOGIN=$(gh api user --jq '.login' 2>/dev/null || printf '')
```

Treat the author as a bot when `COMMENT_AUTHOR_TYPE` is `Bot` or the login ends
with `[bot]`. Treat the author as self when it matches `SELF_LOGIN`.

If the reply path is `thread` and the author is a bot or self, fetch the review
thread node for possible resolution:

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

Offer resolve only when all are true:

- The reply path is `thread`.
- The target thread node was found.
- The thread is not already resolved.
- The original comment author is a bot or the authenticated user.

Prepare a reply preview using placeholder commit hashes until the commit exists:

```markdown
ご指摘ありがとうございます。対応しました。

- Commit: <created-after-commit>
  - <commit subject>
```

Show the user:

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

Ask one plain-text final action question after the preview. Use only the options
that are actually executable:

```text
実装が完了しました。以下のうちどこまで自動実行しますか？

1. コミット & push & 返信 & resolve
2. コミット & push & 返信
3. コミット & push
4. コミットのみ
5. コミットしない
```

Hide `コミット & push & 返信 & resolve` when resolve is not available. Hide
reply options when no reply target could be determined. Renumber the remaining
visible options from `1`.

This unified action selection is the commit decision for this workflow. Do not
ask the generic post-implementation commit question again after using it.

If the user chooses `コミットしない`, stop without git or GitHub side effects.

### Execute Selected Actions

Run only the actions covered by the user's choice. Stop immediately on failure
unless the user explicitly chooses a retry.

Commit:

```bash
PRE_COMMIT_HEAD=$(git rev-parse HEAD)
git status --short
git add <reviewed files>
git commit -m "<drafted message>"
```

Push:

```bash
git push origin HEAD
```

If push fails, ask whether to retry or stop. Do not reply or resolve after a
failed push unless the user explicitly instructs otherwise.

Reply:

Build the actual reply body from the commits created by this workflow:

```bash
git log "${PRE_COMMIT_HEAD}..HEAD" --format='%H %s'
```

Post a thread reply only with:

```bash
gh api "repos/${OWNER}/${REPO}/pulls/${PULL_NUMBER}/comments/${COMMENT_ID}/replies" \
  -X POST -f body="${BODY}"
```

Post a standalone reply only with:

```bash
gh pr comment "${OWNER}/${REPO}#${PULL_NUMBER}" --body "${BODY}"
```

If thread reply fails, report the error and ask whether to retry, downgrade to a
standalone comment, or stop. Warn that downgrading loses thread context. Never
fallback automatically.

Resolve:

Only run resolve when the user selected the resolve option:

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
