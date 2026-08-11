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

## Inputs

```text
$pr-comment-implement <PR_COMMENT_URL> [implementation instructions...]
```

- First token: `PR_URL`; remaining text: `PROMPT`.
- On the final action question, offer an explicit `コミットしない` choice.
- In Plan Mode, the plan artifact is the `<proposed_plan>` block.

## Core Workflow

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

If the current branch differs from `headRefName`, stop before editing. Check
for an existing worktree first — `git worktree list` — since checking out the
PR branch in place can collide with work already in progress in another
worktree:

```bash
git worktree list
```

If a worktree already has `headRefName` checked out, offer using that
worktree's directory as an option alongside checkout / continue on the
current branch / abort. When the worktree option is chosen, run every
subsequent Phase 1–6 command (read, edit, build, test, git add/commit/push)
from that worktree's directory instead of the current one; note the absolute
path in the design (Phase 2) so it survives a context reset. Implementing on
the wrong branch pushes commits the PR never receives.

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

For `REPLY_PATH=thread`, determine the target comment's role before
designing — this is reused in Phase 2's handoff and in Phase 5, and must not
be guessed:

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

# Self: matches the logged-in gh account — a local AI's own posts go through
# this same account, so they count as self too.
IS_SELF=false
[ -n "$SELF_LOGIN" ] && [ "$COMMENT_AUTHOR" = "$SELF_LOGIN" ] && IS_SELF=true
```

If `gh api user` fails, proceed with `IS_SELF=false`. Derive `ROLE` as `bot`
when `IS_BOT`, else `self` when `IS_SELF`, else `other` (bot takes priority
when both would match). For `REPLY_PATH=standalone` (no `COMMENT_ID`), skip
this and treat `ROLE` as not applicable.

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
- 対応種別: code change / no code change
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
  （author: <login>、type: <Bot|User>、role: <self|bot|other>）
- Resolve候補: <thread id and unresolved status, or why resolve is unavailable>
- 実装後の手順: Phase 5 と Phase 6 を必ず継続する
- Reply本文作成: 実装差分、または変更不要の根拠と検証結果を反映して作成する
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

`role` is the `ROLE` value already derived in Phase 1 (`gh api user` vs. the
comment author) — never write a guessed `other` here. A comment authored by
the logged-in account (including one posted by a local AI through that same
account) is `self`, not `other`.

If the analysis shows that the requested behavior already matches repository
conventions or that no code change is warranted, set `NO_CODE_CHANGE=true` in
the design and explain the evidence. Approval of that design authorizes the
no-change workflow below; it does not authorize a GitHub reply yet.

### Phase 3: Implementation (Only after approval)

Implement only the approved scope and update tests when behavior risk
warrants it. Run the
narrowest useful verification command; broaden only when the touched surface
is shared or high risk.

When `NO_CODE_CHANGE=true`, do not edit files or create an empty commit.
Preserve the concrete findings and verification results for the reply body,
then continue to Phase 4.

### Phase 4: Review Changes

Confirm the diff matches the design; check for missing tests or side effects:

```bash
git diff --check
git diff
git status --short
```

When `NO_CODE_CHANGE=true`, confirm that the task introduced no file changes
and report any pre-existing or unrelated changes separately.

### Phase 5: Pre-Action Preparation

Using `REPLY_PATH` / `COMMENT_ID` from Phase 1, resolve all data needed to
commit, push, reply, and possibly resolve.

**⚠️ 原則**: 返信対象が review comment (`#discussion_r{id}`) またはスレッド可能な review comment の場合、**必ずスレッド返信API** (`gh api repos/{owner}/{repo}/pulls/{pull_number}/comments/{comment_id}/replies`) を使用すること。`gh pr comment` は thread API が使えない場合 (純粋な issue comment やスレッド対象が無い review) に限定する。

Unless `NO_CODE_CHANGE=true`, draft a commit message that references the PR
comment, summarizes the change, and follows the repository convention. Do
**not** commit yet. For the no-change workflow, omit commit preparation and
all commit placeholders.

For `thread`, reuse `COMMENT_AUTHOR` / `COMMENT_AUTHOR_TYPE` / `IS_BOT` /
`IS_SELF` / `ROLE` already determined in Phase 1 — do not re-fetch or
re-derive them here.

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
"改善しました". When `NO_CODE_CHANGE=true`, instead state what was inspected,
the concrete evidence, and why no change is warranted. Include `背景・理由`
only when there is a concrete reason for the approach; otherwise omit that
section entirely.

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

For `NO_CODE_CHANGE=true`, use this shape and do not add a `Commit` section:

```
ご指摘ありがとうございます。確認しました。

確認結果:
- {what was inspected and found}

対応方針:
- {why no code change is warranted}
```

Preview with placeholder hashes before commit; fill real hashes after commit.
Before asking the final action question, show the applicable sections below.
Omit the commit-message section when `NO_CODE_CHANGE=true`:

```markdown
## 対応完了。以下を実行する準備ができました。

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
if NO_CODE_CHANGE:
  if CAN_OFFER_RESOLVE:
    add "返信 & resolve"
  if REPLY_PATH in ("thread", "standalone"):
    add "返信のみ"
else:
  if CAN_OFFER_RESOLVE:
    add "コミット & push & 返信 & resolve"
  if REPLY_PATH in ("thread", "standalone"):
    add "コミット & push & 返信"
  add "コミット & push", "コミットのみ"
always add "コミットしない"
```

Question: `対応が完了しました。以下のうちどこまで自動実行しますか？（プレビューは上記参照）`

If the user declines every action (cancel or an equivalent `コミットしない`
choice), stop without git or GitHub side effects and report that. This
question is the commit decision for this workflow; do not ask a generic
post-implementation commit question again.

Execute selected actions sequentially and stop on failure unless retry is chosen.

For `NO_CODE_CHANGE=true`, skip commit and push. Execute a selected reply via
the same thread or standalone API below, then resolve only when that option was
offered and selected. A reply failure still requires the same retry,
standalone-downgrade, or abort decision.

When `NO_CODE_CHANGE=false`, commit:

```bash
PRE_COMMIT_HEAD=$(git rev-parse HEAD)
git add <reviewed files from Phase 4>
git diff --cached --name-only
```

If `git diff --cached --name-only` lists paths you did not stage, unstage
them before continuing.

Immediately before committing, re-check `git rev-parse HEAD` against
`PRE_COMMIT_HEAD`. A mismatch means another process advanced this branch
while you were staging — commonly a parallel session on the same worktree.
Committing anyway risks bundling its changes into your commit or losing
track of what it did. Stop and use `AskUserQuestion` to show the user both
HEAD values and the new commit(s) (`git log <PRE_COMMIT_HEAD>..HEAD --oneline`),
then let them choose: commit your staged changes as-is, re-verify the
staged diff against the new HEAD first, or abort.

```bash
git commit -m "<drafted message>"
```

If the staged diff contains paths beyond what you intended, commit with an
explicit pathspec (`git commit -m "<message>" -- <paths>`) so only your
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
modified files, verification, commit hash/message or an explicit no-change
result, push, reply URL/result, resolve result, and remaining manual action.
