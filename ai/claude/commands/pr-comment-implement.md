---
allowed-tools: Bash(gh:*), Read, Edit, Write, Bash(git:*)
description: "Implement code changes based on PR review comments, with design review phase before implementation."
argument-hint: [prCommentUrl] [instructions...]
effort: max
---

## Instructions

- First `$ARGUMENTS` token is `PR_URL`; the rest is `PROMPT`.
- Fetch context with `gh pr view "$PR_URL" --comments`; it resolves the PR from
  the comment URL.
- Use `AskUserQuestion` for approvals, target selection, retries, and final
  action selection.

## Workflow

### Phase 1: Analysis

Analyze the target comment, `$PROMPT`, affected files, and surrounding code
before designing the change.

### Phase 2: Design Review (MANDATORY)

Before editing, present a Japanese design covering:

- target comment and requested change
- files, code changes, new files, and tests
- affected callers/docs, risks, alternatives, and confirmation points

Ask: `この設計で実装を進めてよろしいですか？修正点があればお知らせください。`
Wait for approval; revise and re-present if requested.

### Phase 3: Implementation (Only after approval)

Implement only the approved scope, preserve unrelated user changes, follow the
codebase style, and update tests when behavior risk warrants it.

### Phase 4: Review Changes

Review modified files, confirm the diff matches the design, and check for
missing tests or side effects.

### Phase 5: Pre-Action Preparation

Before final action selection, resolve all data needed to commit, push, reply,
and possibly resolve.

**⚠️ 原則**: 返信対象が review comment (`#discussion_r{id}`) またはスレッド可能な review comment の場合、**必ずスレッド返信API** (`gh api repos/{owner}/{repo}/pulls/{pull_number}/comments/{comment_id}/replies`) を使用すること。`gh pr comment` は thread API が使えない場合 (純粋な issue comment やスレッド対象が無い review) に限定する。

Draft a commit message that references the PR comment, summarizes the change,
and follows the repository convention. Do **not** commit yet.

Parse `$PR_URL`, extract `OWNER`, `REPO`, `PULL_NUMBER`, then classify the
fragment:

| Fragment pattern | Action |
|---|---|
| `#discussion_r(\d+)` | Extract `COMMENT_ID` → `REPLY_PATH=thread` |
| `#pullrequestreview-(\d+)` | Fetch review comments and resolve concrete target |
| `#issuecomment-(\d+)` or no fragment | `REPLY_PATH=standalone` (no `COMMENT_ID`) |

If unclassified, ask which reply method to use.

For `#pullrequestreview-{review_id}`, fetch inline comments:

```bash
gh api repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/comments \
  --jq '[.[] | {id: .id, path: .path, body: (.body | .[0:80])}]'
```

- 1 comment: use it as `COMMENT_ID`, `REPLY_PATH=thread`.
- Multiple: ask the user to select the target; then `REPLY_PATH=thread`.
- 0: `REPLY_PATH=standalone`.

For `thread`, determine whether the original author is bot/self:

```bash
META=$(gh api "repos/${OWNER}/${REPO}/pulls/comments/${COMMENT_ID}" \
       --jq '{login: .user.login, type: .user.type}')
COMMENT_AUTHOR=$(echo "$META" | jq -r '.login')
COMMENT_AUTHOR_TYPE=$(echo "$META" | jq -r '.type')
SELF_LOGIN=$(gh api user --jq '.login' 2>/dev/null || echo "")

# Bot: type == "Bot" OR login ends with "[bot]"
IS_BOT=false
[ "$COMMENT_AUTHOR_TYPE" = "Bot" ] && IS_BOT=true
case "$COMMENT_AUTHOR" in *"[bot]") IS_BOT=true ;; esac

# Self
IS_SELF=false
[ -n "$SELF_LOGIN" ] && [ "$COMMENT_AUTHOR" = "$SELF_LOGIN" ] && IS_SELF=true
```

If `gh api user` fails, proceed with `IS_SELF=false`.

Only when `REPLY_PATH=thread` and the author is bot/self, fetch the review
thread:

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

THREAD_NODE_ID=$(echo "$THREAD_JSON" | jq -r '.id // empty')
THREAD_IS_RESOLVED=$(echo "$THREAD_JSON" | jq -r '.isResolved // false')
```

Offer resolve only when `REPLY_PATH=thread`, author is bot/self,
`THREAD_NODE_ID` exists, and `THREAD_IS_RESOLVED=false`.

```
ご指摘ありがとうございます。対応しました。

- Commit: {full_hash}
  - {commit_subject}
```

Preview with placeholder hashes before commit; fill real hashes after commit.
Before `AskUserQuestion`, show:

```markdown
## 実装完了。以下を実行する準備ができました。

### コミットメッセージ（草案）
{commit message draft}

### Reply 宛先
- 方法: {Thread reply | Standalone}
- target: comment_id = {id}（author: {login}、type: {Bot|User}、role: {bot|self|other}）
- url: {reply target url}

### Reply 本文プレビュー
{reply body}

### Resolve 対象 thread
- thread_id: {PRRT_...}（現在: unresolved）
（または「対象外: standalone 経路 / 既に resolved / author が他人」）
```

### Phase 6: Unified Action Selection

Use a single `AskUserQuestion`. Build executable options dynamically:

```
if CAN_OFFER_RESOLVE:
  add "コミット & push & 返信 & resolve"
if REPLY_PATH in ("thread", "standalone"):
  add "コミット & push & 返信"
always add "コミット & push", "コミットのみ"
```

Question: `実装が完了しました。以下のうちどこまで自動実行しますか？（プレビューは上記参照）`
If the user selects Other or cancels, do nothing and report that no action was
taken.

Execute selected actions sequentially and stop on failure unless retry is chosen.

Commit:

```bash
git add -A  # or reviewed files from Phase 4
git commit -m "<drafted message>"
BEFORE_SHA=$(git rev-parse origin/$(git branch --show-current) 2>/dev/null || git rev-parse HEAD^)
```

If commit fails, abort before push/reply/resolve.

```bash
git push origin HEAD
```

If push fails, ask retry/abort; skip reply and resolve on abort.

Reply body:

```bash
git log ${BEFORE_SHA}..HEAD --format='%H %s'
```

```bash
# Thread only
gh api "repos/${OWNER}/${REPO}/pulls/${PULL_NUMBER}/comments/${COMMENT_ID}/replies" \
  -X POST -f body="${BODY}"

# Standalone only
gh pr comment "${OWNER}/${REPO}#${PULL_NUMBER}" --body "${BODY}"
```

If thread reply fails, report status/body and ask retry, standalone downgrade, or
abort. Warn before downgrading from `#discussion_r`. Track `REPLY_STATUS`.

```bash
gh api graphql \
  -F id="$THREAD_NODE_ID" \
  -f query='
    mutation($id:ID!){
      resolveReviewThread(input:{threadId:$id}){ thread{ id isResolved } }
    }'
```

Run resolve only when selected. If reply failed, ask before resolving. If
mutation fails or stays unresolved, ask retry/skip.

Final execution summary:

```
## 実行結果
- ✅ Commit: {full_hash} {subject}
- ✅ Push: origin/{branch}
- ✅ Reply: {url} （thread reply）
- ✅ Resolve: thread {PRRT_...} を resolved に変更
```

Use `⚠️` for errors and `⏭️` for skipped steps. Final summary must include
modified files, verification, commit hash/message, push, reply URL/result,
resolve result, and remaining manual action.

## Notes

- Use Read tool to understand existing code before making changes
- Use Edit tool for precise modifications to existing files
- Use Write tool only when creating new files
- Test when applicable and follow project git commit conventions
- Commit / push / reply / resolve are selected in one `AskUserQuestion`
