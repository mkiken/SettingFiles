### Phase 1: Analysis

If `PR_URL` is missing or is not a GitHub PR comment/review URL, ask for it
before proceeding.

Analyze the target comment, `PROMPT`, affected files, and surrounding code
before designing the change.

### Executable boundary in plan mode

Plan mode does not suspend Phase 1. Run every read-only step below (working
tree check, URL parsing, `gh api` GET, thread and file reading) and the 🚀
reaction POST as written — claiming the comment before the approval gate is
the point, and skipping it lets a parallel run pick up the same comment.
Execution stops at `Create an isolated task worktree`: in plan mode, plan that
section instead of running it, and follow the plan-mode variant of Phase 2's
`作業環境引き継ぎ` below.

Check the working tree state first — this must be clean, since Phase 1
creates an isolated task worktree rather than editing in place:

```bash
git status --porcelain
```

If it lists anything, including untracked files, stop. Do not stash, clean,
or reset to force a clean state.

Parse `PR_URL`, extract `OWNER`, `REPO`, `PULL_NUMBER`, then classify the
fragment. The result (`REPLY_PATH`, `COMMENT_ID`, `REACTION_TARGET`) is reused
in later phases:

| Fragment pattern | Action |
|---|---|
| `#discussion_r(\d+)` | Extract `COMMENT_ID` → `REPLY_PATH=thread`, `REACTION_TARGET=repos/${OWNER}/${REPO}/pulls/comments/${COMMENT_ID}` |
| `#pullrequestreview-(\d+)` | Fetch inline comments (below) and resolve concrete target |
| `#issuecomment-(\d+)` | Extract `ISSUE_COMMENT_ID` → `REPLY_PATH=standalone`, `REACTION_TARGET=repos/${OWNER}/${REPO}/issues/comments/${ISSUE_COMMENT_ID}` |

If unclassified, ask which reply method to use.

Whenever a branch above sets `REPLY_PATH=standalone`, also capture the values
needed for the standalone reply's reference header (see Phase 5):
`REPLY_REF_URL` (the original comment's or review's `html_url`),
`REPLY_REF_SUMMARY` (a one-line paraphrase of what it says, composed later in
Phase 5 — not fetched here), and `REPLY_REF_LOCATION` (a short locator string,
when one is meaningful for this branch). For the `#issuecomment-` branch,
fetch the comment body now so Phase 5 can paraphrase it:

```bash
ISSUE_COMMENT_JSON=$(gh api "repos/${OWNER}/${REPO}/issues/comments/${ISSUE_COMMENT_ID}" \
  --jq '{html_url: .html_url, body: .body, login: .user.login, type: .user.type}')
REPLY_REF_URL=$(echo "$ISSUE_COMMENT_JSON" | jq -r '.html_url')
COMMENT_AUTHOR=$(echo "$ISSUE_COMMENT_JSON" | jq -r '.login')
COMMENT_AUTHOR_TYPE=$(echo "$ISSUE_COMMENT_JSON" | jq -r '.type')
```

For `#pullrequestreview-{review_id}`, fetch inline comments:

```bash
gh api repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/comments \
  --jq '[.[] | {id: .id, path: .path, body: (.body | .[0:80])}]'
```

- 1 comment: use it as `COMMENT_ID`, `REPLY_PATH=thread`,
  `REACTION_TARGET=repos/${OWNER}/${REPO}/pulls/comments/${COMMENT_ID}`.
- Multiple: ask the user to select the target; then set `REPLY_PATH=thread`
  and `REACTION_TARGET` as above for the selected comment.
- 0: treat the review as standalone (`REPLY_PATH=standalone`). No single
  comment identifies the review itself, so leave `REACTION_TARGET` unset and
  skip the reaction steps below, reporting why. Fetch the review itself
  (`gh api repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id} --jq
  '{html_url: .html_url, body: .body, login: .user.login, type: .user.type}'`)
  and set `REPLY_REF_URL` to its `html_url`, `COMMENT_AUTHOR` /
  `COMMENT_AUTHOR_TYPE` to its author; leave `REPLY_REF_LOCATION` unset (the
  whole review is the target, no finer locator applies).

Regardless of the inline-comment count, when `PROMPT` identifies a finding
that matches no inline comment — e.g. one listed only in the review **body**
(such as a "diff 範囲外のため行コメント不可" section) — fetch the review body
(`gh api repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id} --jq
'{html_url: .html_url, body: .body, login: .user.login, type: .user.type}'`)
to locate it, skip the target-selection question, and treat it like the
0-comment case: `REPLY_PATH=standalone`, `REACTION_TARGET` unset, reaction and
resolve reported as not applicable. Set `REPLY_REF_URL` / `COMMENT_AUTHOR` /
`COMMENT_AUTHOR_TYPE` from this same fetch, and set `REPLY_REF_LOCATION` to a
short phrase naming where in the review body the finding lives (e.g.
「レビュー本文の『diff 範囲外』節」).

### React to the target comment (🚀)

As soon as `REACTION_TARGET` is known, mark the comment as being worked on so
parallel `cl-pci` / `cx-pci` runs don't pick up the same comment twice. Do
this before Phase 2's approval gate — visibility into what's claimed matters
more than waiting for approval.

```bash
ROCKET_REACTION_ID=$(gh api "${REACTION_TARGET}/reactions" -X POST -f content=rocket --jq '.id')
```

Reaction calls are best-effort and never block the workflow: if this fails,
report a warning and continue. A repeat reaction from the same account
returns the existing reaction (HTTP 200), so this is safe to retry. Carry
`ROCKET_REACTION_ID` forward into Phase 2's handoff section so it survives a
context reset; if it's lost later, re-derive it with
`gh api "${REACTION_TARGET}/reactions" --jq '.[] | select(.user.login == $SELF_LOGIN and .content == "rocket") | .id'`.

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

From step 1's fetch, also keep `REPLY_REF_URL` (`.html_url`),
`REPLY_REF_LOCATION` (`` `{.path}:{.line}` ``, when `.line` is present), and
the comment body for a later paraphrase. `REPLY_PATH` is `thread` here, so
none of this is used unless Phase 6 downgrades to standalone — it is kept
only so that downgrade doesn't need a second fetch.

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

Read affected files, surrounding code, and the closest existing test. If the
comment targets stale code, inspect the current equivalent symbol or concept.
For a security finding already fixed in code, confirm the test asserts the
requested mitigation's observable output—not merely a malicious fixture or an
unrelated property—before setting `NO_CODE_CHANGE`; otherwise plan a focused
regression test.

When a relevant targeted baseline check fails, inspect `git blame` and `git
log -S` for the failed symbol or test before asking to expand scope. If Git
evidence shows a current-PR or prior review-response change left a directly
dependent update incomplete, include the smallest correction in the
`implement` scope and record the evidence. Otherwise treat it as unrelated
baseline state and ask the user whether to expand scope.

### Decide whether the comment should be acted on (MANDATORY)

Do not treat the review comment as an implementation order. Before designing
any change, evaluate its exact claim against repository evidence:

- current behavior in the affected code and its callers;
- the complete review thread, repository requirements, and established
  conventions that reveal the intended behavior;
- the closest tests and whether they already prove or contradict the claim;
- the requested change's scope, regression risk, and effect on correctness,
  security, or maintainability.

The comment author's role or authority is not evidence that the claim is
correct. Record the concrete evidence inspected, then set
`COMMENT_DISPOSITION` to exactly one value:

- `implement`: the claim is valid, unaddressed, in scope, and the requested
  outcome is supported by repository evidence. Set `NO_CODE_CHANGE=false`.
- `reject`: the premise is incorrect, conflicts with intended behavior, is out
  of scope, or would make the code worse. Set `NO_CODE_CHANGE=true`.
- `already-satisfied`: current code already provides the requested behavior.
  Set `NO_CODE_CHANGE=true`; require a test that observes the claimed behavior
  when risk warrants it.
- `needs-user-decision`: evidence is missing or conflicting, or the comment
  requires a product or compatibility tradeoff the repository cannot settle.
  Do not default to implementation or no change.

For `needs-user-decision`, stop before Phase 2 and ask a focused question that
shows the competing options, evidence for each, and their behavior and risk.
Use the answer to replace `needs-user-decision` with `implement`, `reject`, or
`already-satisfied`; Phase 2 must not begin while the disposition is
unresolved.

### Create an isolated task worktree

Implement in a dedicated worktree, not the invoking one, so parallel
`cl-pci` / `cx-pci` runs against the same PR never share a working tree.

In plan mode, stop executing here: plan this section and everything after it,
and do not run `git fetch`, `wtc`, or the Herdr context helper. Create the
worktree at the start of Phase 3, immediately after approval and before any
edit.

```bash
ORIGINAL_PATH=$(git rev-parse --show-toplevel)
HEAD_BRANCH=$(gh pr view "$PR_URL" --json headRefName --jq .headRefName)
```

Ensure a local ref for `HEAD_BRANCH` exists (fetch it if this is the first
time this repo has seen that branch) — it only needs to exist as a ref to
serve as the worktree's `--base`; nothing needs to check it out:

```bash
git show-ref --verify --quiet "refs/heads/${HEAD_BRANCH}" || \
  git fetch origin "${HEAD_BRANCH}:${HEAD_BRANCH}"
```

Confirm `wtc` and `wtm` are available in the configured interactive Zsh from
the original worktree; stop with a clear setup error if either is missing:

```bash
zsh -ic 'builtin cd -q -- "$1" && type wtc >/dev/null && type wtm >/dev/null' zsh "$ORIGINAL_PATH"
```

Load `herdr-tab-label` and derive a slug from the comment/`PROMPT` using its
shared rules. Form `TASK_BRANCH="task/<slug>-<timestamp>"`; if that local
branch exists, append `-2`, `-3`, ... until unused. Record that
`refs/heads/<task-branch>` is absent before creating the worktree — this
proves ownership for later cleanup.

Create the worktree through the same executable boundary `worktree-task`
uses: keep the `-c` script literal, pass paths/branches only as positional
arguments, never interpolate task-derived values into the script string.
That reference covers the invocation mechanics only — do not carry over
`worktree-task`'s own plan-mode or handoff rules, which govern that skill's
entry point, not this workflow's.

```bash
zsh -ic 'builtin cd -q -- "$1" && wtc "$2" --base "$3" --no-cd' zsh "$ORIGINAL_PATH" "$TASK_BRANCH" "$HEAD_BRANCH"
```

Capture the exit status; a nonzero result may still have partially created a
branch or worktree, so don't assume it created nothing. Never infer the new
path from command output — re-read `git worktree list --porcelain`, match the
unique `branch refs/heads/<task-branch>` entry, and record its `worktree`
path as `TASK_PATH`. If the match is missing or not unique, or the task
worktree's branch/`HEAD` don't match the recorded original `HEAD`, treat this
like `worktree-task`'s post-invocation failure handling: gather read-only Git
evidence, and only clean up when every ownership invariant (branch was absent
beforehand, exactly one matching worktree, `HEAD` equals the recorded value,
working tree clean, no operation in progress) is proven. Otherwise preserve
all state and report it.

When `HERDR_ENV=1`:

```bash
herdr_context_helper="${SET:-$HOME/Desktop/repository/SettingFiles}/shell/tmux/herdr_worktree_context.sh"
zsh -ic 'builtin cd -q -- "$1" && source "$2" && set_herdr_task_worktree_context "$3"' zsh "$ORIGINAL_PATH" "$herdr_context_helper" "$TASK_PATH"
```

Then apply `herdr-tab-label` from `ORIGINAL_PATH` using the slug alone (not
the `task/` namespace or timestamp). Both steps are fail-safe: report a
warning and continue on failure rather than blocking the task.

From this point on, run every Phase 1–6 command (read, edit, build, test, git
add/commit) from `TASK_PATH`, not `ORIGINAL_PATH`. `ORIGINAL_PATH` is only
touched again for the merge-back in Phase 6.

#### Constrain project-mandated workflows to the task worktree

At Phase 3, repository instructions may require another project workflow
before the first implementation write. Invoke it from `TASK_PATH` only, and
resolve its artifact roots, output paths, branch changes, and worktree changes
before allowing its first write. Every write target must remain inside
`TASK_PATH`, and the workflow must stay on `TASK_BRANCH` without creating
another worktree.

If a required workflow resolves any write target outside `TASK_PATH`
(including a planning directory under `ORIGINAL_PATH`), stop before that write
and before implementation. Do not silently skip the required workflow or treat
read-only initialization as satisfying it. Report the exact external target
and the conflicting repository/worktree requirements so the user can correct
the workflow configuration or choose a compatible execution path.

### Phase 2: Design Review (MANDATORY)

Before editing, present this Japanese design and wait for explicit approval:

```markdown
## 実装設計

### 対応するコメント
- URL:
- 種別: review thread / review / standalone
- 要旨:

### 採否判断
- 判定: 対応する / 対応不要 / 既対応
- 指摘の前提:
- 確認した証拠:
- 判断理由:

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

### 作業環境引き継ぎ
- Task worktree: <TASK_PATH、または plan mode のため未作成>
- Task branch: <task/slug-timestamp、または plan mode のため未作成（実装開始時に採番）>
- Merge target (PR head): <HEAD_BRANCH>
- Invoking worktree: <ORIGINAL_PATH>
- Rocket reaction ID: <ROCKET_REACTION_ID、または再取得が必要な旨>

この設計で実装を進めてよろしいですか？修正点があればお知らせください。
```

Wait for approval; revise and re-present if requested. Do not edit before
approval.

If the user declines (an explicit abort rather than requesting revisions),
remove the 🚀 reaction (best-effort) and clean up the task worktree/branch
under the same ownership-proof rule described above, then report the
preserved or removed state.

`PR返信引き継ぎ` and `作業環境引き継ぎ` must survive context reset with enough reply/resolve-target and worktree-directory details for the next worker to resume. If a target remains unresolved before implementation, name the exact item to re-fetch. In plan mode, put the design, including both sections, in the platform plan artifact.

In plan mode the task worktree does not exist yet, so `作業環境引き継ぎ` records
intent instead of resolved paths: state that the worktree is uncreated and that
the implementer must start at `Create an isolated task worktree` before any
edit. `Rocket reaction ID` is still a real value — the reaction was posted in
Phase 1 — so record it, not a placeholder. Decline cleanup then only removes
the 🚀 reaction; there is no worktree or branch to clean up.

`role` is the `ROLE` value already derived in Phase 1 (`gh api user` vs. the
comment author) — never write a guessed `other` here. A comment authored by
the logged-in account (including one posted by a local AI through that same
account) is `self`, not `other`.

The mandatory Phase 1 disposition controls the design: `implement` uses
`NO_CODE_CHANGE=false`; `reject` and `already-satisfied` use
`NO_CODE_CHANGE=true`. Explain the evidence and reasoning in `採否判断`; do not
collapse a `needs-user-decision` result into either path without the user's
choice. Approval of a no-change design authorizes the no-change workflow
below; it does not authorize a GitHub reply yet.

### Phase 3: Implementation (Only after approval)

Work only inside `TASK_PATH`. Never edit `ORIGINAL_PATH`.

Implement only the approved scope and update tests when behavior risk
warrants it. Run the
narrowest useful verification command; broaden only when the touched surface
is shared or high risk.

When `NO_CODE_CHANGE=true`, do not edit files or create an empty commit.
Preserve the concrete findings and verification results for the reply body,
then continue to Phase 4.

### Phase 4: Review Changes

Confirm the diff matches the design; check for missing tests or side effects.
Run these from `TASK_PATH`:

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
herdr_context_helper="${SET:-$HOME/Desktop/repository/SettingFiles}/shell/tmux/herdr_worktree_context.sh"
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
