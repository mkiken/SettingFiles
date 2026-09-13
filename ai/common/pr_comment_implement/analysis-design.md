### Phase 1: Analysis

If `PR_URL` is missing or is not a GitHub PR comment/review URL, ask for it
before proceeding.

Analyze the target comment, `PROMPT`, affected files, and surrounding code
before designing the change.

### Executable boundary in plan mode

Plan mode does not suspend Phase 1. Run every read-only step below (working
tree check, URL parsing, `gh api` GET, thread and file reading), but skip the
🚀 reaction POST and worktree creation because both mutate state. Continue the
remaining read-only analysis through Phase 2 and follow its plan-mode handoff.
After approval, the implementer posts the deferred reaction, then starts at
`Create an isolated task worktree` before editing.

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
  Set `NO_CODE_CHANGE=true`. If no existing test pins that behavior, add a
  regression test that observes it; if an existing test already pins it, add
  none and record which test that is.
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
deferred 🚀 reaction and then the worktree immediately after approval and
before any edit.

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
herdr_context_helper="${SET:-$HOME/Desktop/repository/SettingFiles}/shell/herdr/herdr_worktree_context.sh"
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
- Rocket reaction ID: <ROCKET_REACTION_ID、plan mode のため未作成、または再取得が必要な旨>

この設計で実装を進めてよろしいですか？修正点があればお知らせください。
```

Wait for approval; revise and re-present if requested. Do not edit before
approval.

If the user declines (an explicit abort rather than requesting revisions),
remove the 🚀 reaction (best-effort) and clean up the task worktree/branch
under the same ownership-proof rule described above, then report the
preserved or removed state.

`PR返信引き継ぎ` and `作業環境引き継ぎ` must survive context reset with enough reply/resolve-target and worktree-directory details for the next worker to resume. If a target remains unresolved before implementation, name the exact item to re-fetch. In plan mode, put the design, including both sections, in the platform plan artifact.

In plan mode the reaction and task worktree do not exist yet, so
`作業環境引き継ぎ` records intent instead of resolved values: state that the
reaction is deferred, that the worktree is uncreated, and that the implementer
must post the 🚀 reaction and then start at `Create an isolated task worktree`
before any edit. If the user declines, there is no reaction, worktree, or
branch to clean up.

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
