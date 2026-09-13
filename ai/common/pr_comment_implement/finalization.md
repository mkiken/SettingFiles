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

When `REPLY_PATH=standalone`, prepend a reference header to either shape above
so the reply is self-contained on the PR timeline instead of appearing as an
unrelated top-level comment — `gh pr comment` posts with no thread context:

```
> 返信対象: [{one-line paraphrase}]({REPLY_REF_URL})
> （{auxiliary info, only what is available}）

ご指摘ありがとうございます。...
```

- `{one-line paraphrase}` is composed from the original comment/review body —
  compress its point to one line; never paste the raw text verbatim or use a
  vague restatement.
- The second header line lists only auxiliary info that was actually
  captured in Phase 1 — `` `{file}:{line}` `` when the original review
  comment's path/line is known (thread-downgrade case below), `@{login}` when
  `COMMENT_AUTHOR` is known, or `REPLY_REF_LOCATION` when set. Join whatever
  is available with ` / `; omit the entire second line when nothing is
  available. Never emit a placeholder for a value that wasn't captured.
- For `REPLY_PATH=thread`, omit this header entirely — GitHub already renders
  the reply inside its thread.

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
    add "コミット & 親ブランチにマージ & push & 返信 & resolve"
  if REPLY_PATH in ("thread", "standalone"):
    add "コミット & 親ブランチにマージ & push & 返信"
  add "コミット & 親ブランチにマージ & push"
  add "コミット & 親ブランチにマージ"
  add "コミットのみ"
always add "コミットしない"
```

Question: `対応が完了しました。以下のうちどこまで自動実行しますか？（プレビューは上記参照）`

Use the platform's confirmation primitive only when it can display every
executable option. If its option limit is lower, ask this one final question
as a plain-text ordered list of every option and accept a number-only reply.
Never omit or group executable options to fit the UI limit.

If the user declines every action (cancel or an equivalent `コミットしない`
choice), stop without git or GitHub side effects and report that. This
question is the commit decision for this workflow; do not ask a generic
post-implementation commit question again.

Execute selected actions sequentially and stop on failure unless retry is chosen.

For `NO_CODE_CHANGE=true`, skip commit, merge, and push — `TASK_PATH` stays
clean at the recorded original `HEAD`, so there is nothing to merge back.
Execute a selected reply via the same thread or standalone API below, then
resolve only when that option was offered and selected. A reply failure still
requires the same retry, standalone-downgrade, or abort decision. On success,
react (below), then remove the task worktree/branch directly from
`ORIGINAL_PATH` (`git worktree remove` then `git branch -d`, verifying both
are gone) and clear the Herdr task-worktree context.

When `NO_CODE_CHANGE=false`, commit (run from `TASK_PATH`):

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

If commit fails, abort before merge/push/reply/resolve.

If the selection was `コミットのみ`, stop here: do not merge or push. Report
`TASK_PATH` and `TASK_BRANCH` as preserved, and leave the 🚀 reaction in place
(work is still in progress from the PR's perspective).

#### Merge the task branch back into the PR head

Run from `TASK_PATH`, through the same executable boundary as worktree
creation. This performs `wtm <HEAD_BRANCH>` semantics — fast-forward when
possible, otherwise a merge commit; never squash or rebase:

```bash
zsh -ic 'builtin cd -q -- "$1" && wtm "$2"' zsh "$TASK_PATH" "$HEAD_BRANCH"
```

If `wtm` returns nonzero, first run `git status --porcelain` in
`ORIGINAL_PATH`. When it is dirty with changes this task did not make
(typically a parallel session working in the invoking worktree; `wtm` refuses
with "target worktree has uncommitted changes"), do not stash, reset, or
otherwise alter them — the task commit is safe on `TASK_BRANCH`. Ask via the
user-confirmation mechanism whether to wait for the parallel work to be
committed and then retry the same `wtm` invocation (re-verify the target is
clean first), or to stop with all state preserved.

Otherwise check for real conflicts
(`git diff --name-only --diff-filter=U` / `git ls-files -u` in
`ORIGINAL_PATH`) rather than assuming failure. When conflicts exist:

1. Report every conflicted path with a concrete resolution proposal.
2. Ask exactly `提案を適用` (resolve in `ORIGINAL_PATH` as proposed, stage
   each path explicitly, continue the merge — never rebase) or `自分で解決`
   (preserve merge state, task worktree, and task branch; stop).
3. After a successful agent-applied continuation, `wtm` cannot run its own
   cleanup — manually run `git worktree remove` for `TASK_PATH` from
   `ORIGINAL_PATH`, then `git branch -d` for `TASK_BRANCH`, then verify both
   are gone.

When `wtm` failed without conflicts, check whether the task commit is already
an ancestor of `HEAD_BRANCH` — if so, do not retry; just run the independent
checks below. Otherwise preserve all state (`ORIGINAL_PATH`, `TASK_PATH`,
`TASK_BRANCH`), record the exact failure output, and report the blocking
state without stashing, resetting, or otherwise altering either worktree to
force the merge through.

After merge success (including a resolved-conflict continuation),
independently verify — never trust `wtm`'s own cleanup:

- Merge: re-read `ORIGINAL_PATH`'s branch and `HEAD`; require the task commit
  to be an ancestor of `HEAD_BRANCH`; confirm `ORIGINAL_PATH` is clean.
- Cleanup: require the task worktree entry to be absent and
  `refs/heads/<task-branch>` to not exist.

If merge succeeded but cleanup didn't, do not push — report the remaining
worktree/branch and the failed check.

Once cleanup is verified, clear the Herdr task-worktree context (fail-safe,
warn and continue on failure):

```bash
herdr_context_helper="${SET:-$HOME/Desktop/repository/SettingFiles}/shell/herdr/herdr_worktree_context.sh"
zsh -ic 'builtin cd -q -- "$1" && source "$2" && clear_herdr_task_worktree_context' zsh "$ORIGINAL_PATH" "$herdr_context_helper"
```

If the selection was `コミット & 親ブランチにマージ`, stop here. Report the
local `HEAD_BRANCH` and merged commit; skip fetch, push, reply, and resolve.
Leave the 🚀 reaction in place because the PR head has not been updated on
GitHub yet.

#### Push, handling a racing remote

Run this section only when the selected action contains `& push`.

Parallel `cl-pci` / `cx-pci` runs against the same PR merge back into the
same `HEAD_BRANCH` and can race here. Run from `ORIGINAL_PATH`:

```bash
git fetch origin "+refs/heads/${HEAD_BRANCH}:refs/remotes/origin/${HEAD_BRANCH}"
git rev-list --left-right --count "HEAD...origin/${HEAD_BRANCH}"
```

If `origin/${HEAD_BRANCH}` is ahead or history diverged, show the ahead
commits (`git log HEAD..origin/${HEAD_BRANCH} --oneline`) and ask exactly
`pull して再push` or `中断`:

- `pull して再push`: `git pull --ff-only origin "$HEAD_BRANCH"`; if that's not
  possible, merge (never rebase, never force) and re-run this check before
  pushing.
- `中断`: do not push. Report the local merged branch and commit as
  preserved; skip reply and resolve.

Never force-push.

```bash
git push origin HEAD
```

If push fails for a reason other than the race just handled, ask retry/abort;
skip reply and resolve on abort. After a successful push, refresh the tracking
ref and require its object ID to equal the pushed commit before reporting the
push as successful:

```bash
git fetch origin "+refs/heads/${HEAD_BRANCH}:refs/remotes/origin/${HEAD_BRANCH}"
```

Commit list for the reply body:

```bash
git log "${PRE_COMMIT_HEAD}..HEAD" --format='%H %s'
```

Fill the previewed reply body's `Commit` section with this output; do not
replace the body with only commit lines.

The reply body is multi-line and may contain backticks or `$(...)`-like
sequences. Write it to a temp file with the `Write` tool first (never build it
via a shell heredoc or command substitution passed inline to `gh`), then pass
it by file reference — never inline the body text into the shell command
string:

```bash
# Thread only
gh api "repos/${OWNER}/${REPO}/pulls/${PULL_NUMBER}/comments/${COMMENT_ID}/replies" \
  -X POST -F body=@"${BODY_FILE}"

# Standalone only
gh pr comment "${PULL_NUMBER}" -R "${OWNER}/${REPO}" --body-file "${BODY_FILE}"
```

If thread reply fails, report status/body and ask retry, standalone downgrade,
or abort; never fall back automatically. Warn that downgrading from
`#discussion_r` loses thread context, but that the reply body will carry a
reference header linking back to it (Phase 5). Track `REPLY_STATUS`.

On standalone downgrade, the reply body was originally composed for a thread
reply and has no reference header yet — prepend one now, following Phase 5's
standalone rule, using the `REPLY_REF_URL` / `REPLY_REF_LOCATION` already kept
from Phase 1's target-comment fetch and a one-line paraphrase of its body.

### React to the target comment (🎉)

Once the reply succeeds (`REPLY_STATUS` OK), swap the reaction — best-effort,
warn and continue on failure, and skip entirely if `REACTION_TARGET` was
never set:

```bash
gh api "${REACTION_TARGET}/reactions/${ROCKET_REACTION_ID}" -X DELETE
gh api "${REACTION_TARGET}/reactions" -X POST -f content=hooray
```

If `ROCKET_REACTION_ID` is unavailable, re-derive it first (Phase 1) before
deleting; if it still can't be found, skip the delete and still add 🎉.

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

### Abort or decline cleanup

If the user chooses `コミットしない`, or any step above stops with `abort`,
remove the 🚀 reaction (best-effort) before reporting — a preserved task
worktree with no forward progress shouldn't keep showing as claimed on
GitHub. Leave `TASK_PATH` and `TASK_BRANCH` intact for manual continuation
unless a merge already completed.

### Verify the final reaction state

Before printing the summary, confirm the reaction on GitHub matches what the
chosen action implies — a silently failed POST or DELETE otherwise ships as a
wrong claim signal. Skip only when `REACTION_TARGET` was never set; report the
reaction as `⏭️` then.

Expected state by outcome:

| Outcome | Expected |
| --- | --- |
| `コミットのみ` | 🚀 only |
| `コミット & 親ブランチにマージ` (no push) | 🚀 only |
| Push and reply succeeded | 🎉 only |
| Design declined, `コミットしない`, or any `abort` | none |

```bash
gh api "${REACTION_TARGET}/reactions" \
  --jq ".[] | select(.user.login == \"${SELF_LOGIN}\") | \"\(.content) \(.id)\""
```

`SELF_LOGIN` comes from Phase 1; re-derive it with `gh api user --jq '.login'`
if it was lost. Compare the listing against the expected state and reconcile
once:

- Expected reaction missing → `gh api "${REACTION_TARGET}/reactions" -X POST -f content=<rocket|hooray>`
- Unexpected reaction present → `gh api "${REACTION_TARGET}/reactions/<id>" -X DELETE` using the id from the listing

Re-run the GET after reconciling. This step is mandatory: never print the
summary without either a verified matching state or an explicit failure line.
Stop after one reconcile pass — if the GET fails or the state still mismatches,
report `⚠️ Reaction: expected <X>, actual <Y>（手動修正が必要）` naming the exact
`gh api` command to run by hand.

Final execution summary:

```
## 実行結果
- ✅ Commit: {full_hash} {subject}
- ✅ Merge: task branch → {HEAD_BRANCH}
- ✅ Push: origin/{HEAD_BRANCH}
- ✅ Reply: {url} （thread reply）
- ✅ Reaction: 🚀 → 🎉
- ✅ Resolve: thread {PRRT_...} を resolved に変更
```

Use `⚠️` for errors and `⏭️` for skipped steps. Final summary must include
modified files, verification, commit hash/message or an explicit no-change
result, merge result, push, reply URL/result, reaction result (the verified
state, not the intended one), resolve result, and remaining manual action.
