### Phase 1: Analysis

If `PR_URL` is missing or is not a GitHub PR comment/review URL, ask for it
before proceeding.

Analyze the target comment, `PROMPT`, affected files, and surrounding code
before designing the change.

Check the working tree state and branch alignment first:

```bash
git status --short
git branch --show-current
gh pr view "$PR_URL" --json headRefName --jq .headRefName
```

If the current branch differs from `headRefName`, stop before editing and ask:
checkout the PR branch / continue on the current branch / abort. Implementing
on the wrong branch pushes commits the PR never receives.

Parse `PR_URL`, extract `OWNER`, `REPO`, `PULL_NUMBER`, then classify the
fragment. The result (`REPLY_PATH`, `COMMENT_ID`) is reused in Phase 5:

| Fragment pattern | Action |
|---|---|
| `#discussion_r(\d+)` | Extract `COMMENT_ID` → `REPLY_PATH=thread` |
| `#pullrequestreview-(\d+)` | Fetch inline comments (below) and resolve concrete target |
| `#issuecomment-(\d+)` | `REPLY_PATH=standalone` (no `COMMENT_ID`) |

If unclassified, ask which reply method to use.

For `#pullrequestreview-{review_id}`, fetch inline comments:

```bash
gh api repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/comments \
  --jq '[.[] | {id: .id, path: .path, body: (.body | .[0:80])}]'
```

- 1 comment: use it as `COMMENT_ID`, `REPLY_PATH=thread`.
- Multiple: ask the user to select the target; then `REPLY_PATH=thread`.
- 0: treat the review as standalone (`REPLY_PATH=standalone`).

When `REPLY_PATH=thread`, always read the complete review thread before
designing the change:

1. Fetch the target comment:
   `gh api "repos/${OWNER}/${REPO}/pulls/comments/${COMMENT_ID}"`.
2. `ROOT_COMMENT_ID` = `in_reply_to_id` when present, else the target `id`.
3. Fetch all PR review comments:
   `gh api "repos/${OWNER}/${REPO}/pulls/${PULL_NUMBER}/comments" --paginate`.
4. Filter to `id == ROOT_COMMENT_ID` or `in_reply_to_id == ROOT_COMMENT_ID`,
   sorted by `created_at`.

The URL target is primary; same-thread replies are required context. Reflect
their corrections, constraints, or implementation intent in the design.

Read affected files and surrounding code. If the comment targets stale code,
inspect the current equivalent symbol or concept.

### Phase 2: Design Review (MANDATORY)

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

### PR返信引き継ぎ
- Reply方式: thread reply / standalone / なし
- Reply target: <comment_id or pull number, or なし>
- Resolve候補: <thread id and unresolved status, or why resolve is unavailable>
- 実装後の手順: Phase 5 と Phase 6 を必ず継続する
- Reply本文作成: 実装差分、検証結果、作成commitを反映して実装後に作成する
- 省略禁止: context reset後もPRへの返信とresolve判断を省略しない

この設計で実装を進めてよろしいですか？修正点があればお知らせください。
```

Wait for approval; revise and re-present if requested. Do not edit before
approval.

The `PR返信引き継ぎ` section is the handoff that survives a context reset: it
must give the next worker enough reply/resolve target information to continue
the GitHub response workflow. If a target cannot be fully determined before
implementation, state the exact item to re-fetch instead of omitting it. In
plan mode, write this design (including that section) into the platform's
plan artifact.

### Phase 3: Implementation (Only after approval)

Implement only the approved scope, preserve unrelated user changes, follow the
codebase style, and update tests when behavior risk warrants it. Run the
narrowest useful verification command; broaden only when the touched surface
is shared or high risk.

### Phase 4: Review Changes

Confirm the diff matches the design; check for missing tests or side effects:

```bash
git diff --check
git diff
git status --short
```

### Phase 5: Pre-Action Preparation

Using `REPLY_PATH` / `COMMENT_ID` from Phase 1, resolve all data needed to
commit, push, reply, and possibly resolve.

**⚠️ 原則**: 返信対象が review comment (`#discussion_r{id}`) またはスレッド可能な review comment の場合、**必ずスレッド返信API** (`gh api repos/{owner}/{repo}/pulls/{pull_number}/comments/{comment_id}/replies`) を使用すること。`gh pr comment` は thread API が使えない場合 (純粋な issue comment やスレッド対象が無い review) に限定する。

Draft a commit message that references the PR comment, summarizes the change,
and follows the repository convention. Do **not** commit yet.

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

If `THREAD_JSON` is empty, the thread may lie outside the `first:100` window;
report resolve as unavailable for that reason instead of silently skipping it.

Offer resolve only when `REPLY_PATH=thread`, author is bot/self,
`THREAD_NODE_ID` exists, and `THREAD_IS_RESOLVED=false`.

Compose the reply body from the implemented diff and the original review
comment, naming what changed — no vague bullets such as "修正しました" or
"改善しました". Include `背景・理由` only when there is a concrete reason for
the approach; otherwise omit that section entirely.

```
ご指摘ありがとうございます。対応しました。

対応概要:
- {what was changed}

背景・理由:
- {why this approach was chosen, only when there is a concrete reason}

Commit:
- {full_hash}
  - {commit_subject}
```

Preview with placeholder hashes before commit; fill real hashes after commit.
Before asking the final action question, show:

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

When displaying this preview, use a fence longer than the longest backtick run
in the embedded content (e.g. ````markdown) — the reply body and commit
message draft may contain code blocks.

### Phase 6: Unified Action Selection

Ask one final action question. Build the options dynamically and show only
executable options:

```
if CAN_OFFER_RESOLVE:
  add "コミット & push & 返信 & resolve"
if REPLY_PATH in ("thread", "standalone"):
  add "コミット & push & 返信"
always add "コミット & push", "コミットのみ"
```

Question: `実装が完了しました。以下のうちどこまで自動実行しますか？（プレビューは上記参照）`

If the user declines every action (cancel or an equivalent `コミットしない`
choice), stop without git or GitHub side effects and report that. This
question is the commit decision for this workflow; do not ask a generic
post-implementation commit question again.

Execute selected actions sequentially and stop on failure unless retry is chosen.

Commit:

```bash
PRE_COMMIT_HEAD=$(git rev-parse HEAD)
git add <reviewed files from Phase 4>
git diff --cached --name-only
git commit -m "<drafted message>"
```

If `git diff --cached --name-only` lists paths you did not stage, commit with
an explicit pathspec (`git commit -m "<message>" -- <paths>`) so only your
paths are committed.

If commit fails, abort before push/reply/resolve.

```bash
git push origin HEAD
```

If push fails, ask retry/abort; skip reply and resolve on abort.

Commit list for the reply body:

```bash
git log "${PRE_COMMIT_HEAD}..HEAD" --format='%H %s'
```

Fill the previewed reply body's `Commit` section with this output; do not
replace the body with only commit lines.

```bash
# Thread only
gh api "repos/${OWNER}/${REPO}/pulls/${PULL_NUMBER}/comments/${COMMENT_ID}/replies" \
  -X POST -f body="${BODY}"

# Standalone only
gh pr comment "${PULL_NUMBER}" -R "${OWNER}/${REPO}" --body "${BODY}"
```

If thread reply fails, report status/body and ask retry, standalone downgrade,
or abort; never fall back automatically. Warn that downgrading from
`#discussion_r` loses thread context. Track `REPLY_STATUS`.

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
