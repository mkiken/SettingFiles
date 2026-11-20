---
name: pr-comment-implement-batch
description: Handle all unresolved review threads, review bodies and human issue comments of the current branch's PR in one run - choose items to skip, then commit and reply per item, and resolve bot/self threads. Use for an explicit batch PR-comment request.
---

# PR Comment Implement (Batch)

Run once in the current terminal on the current branch (no worktree). Additional
request text is emphasis only, never permission to select another PR or skip an
approval. Handles unresolved review threads plus two kinds that have no resolve
state: review bodies (the overall comment submitted with "Review changes") and
issue comments.

Resolve this skill directory's real path; its grandparent is `ai/common`. Read
`pr_comment_implement/analysis-design.md` there, only its "Decide whether the
comment should be acted on" section (dispositions `implement`, `reject`,
`already-satisfied`, `needs-user-decision`). Stop if it cannot be read.

## Establish the target

Read the repository instructions first. Run
`gh pr view --json number,url,state,baseRefOid,headRefOid,headRefName`. Require
an attached branch equal to headRefName, HEAD equal to headRefOid, an OPEN PR,
and empty `git status --porcelain` including untracked files; otherwise stop
with the failed condition. Never checkout, stash or reset to proceed. Record
repository, PR number, branch and head OID.

## Collect items

Threads: query GraphQL `reviewThreads(first:100)` with `id isResolved isOutdated path
line comments(first:100){nodes{databaseId author{login __typename} body
createdAt url}}`. Keep only `isResolved=false`. If more than 100 threads exist,
say the list is truncated and handle what was fetched.

Review bodies: query GraphQL `reviews(first:100){nodes{author{login
__typename} body submittedAt url}}`. Keep those whose body, after removing HTML
comments (`<!-- ... -->`) and trimming, is non-empty and whose ROLE is not
`self`. Also drop a ROLE `bot` review body that carries no finding of its own:
a review notice, change summary, usage or configuration tips, a pointer to its
inline comments, or only findings repeated in that review's inline threads.
Keep it when unsure. Do not number dropped bodies; after the list, print one
line `除外: bot通知本文 N件（@login, ...）`.

Issue comments: `gh api repos/{owner}/{repo}/issues/{n}/comments --paginate`.
Keep only ROLE `other` (exclude `bot` and `self`).

For review bodies and issue comments, mark `already-replied-by-me` when a
`self` issue comment posted after the item contains the item's `html_url` (the
standalone reply header embeds that URL).

ROLE of an item = its author (for a thread, its root comment author): `bot`
when `__typename` is `Bot` or the login ends with `[bot]`; else `self` when it
equals `gh api user --jq .login`; else `other` (bot wins over self). This
applies to all three kinds.

## Skip selection

Before anything else, list items as `n. [thread|review-body|issue-comment]
[path:line or -] @author (role, outdated, already-replied-by-me) summary`. Ask
which numbers to skip (none / numbers) via the platform's user-confirmation
mechanism. Skipped items are untouched. Stop if none remain.

## Choose flow

If every remaining item is a small, local fix with no open design decision,
recommend Inline; otherwise recommend Subagents. Let the user choose.

- Inline: the main session performs the Analyst brief per item, in order.
- Subagents: one read-only subagent per item, launched together (Claude: Task
  general-purpose; Codex: spawn). Prompt in a few lines: read this SKILL.md's
  "Analyst brief" and follow it; payload = full item text (kind included), ROLE, repo, PR
  number, head OID. Subagents never edit, commit or post.

## Analyst brief

Read the complete item, the affected code, callers and closest tests. Apply
the disposition rules from analysis-design.md. Return: disposition, evidence
inspected, files to change, change plan, test conditions with expected results.
Edit nothing.

## Per-item loop

Strictly serial, in list order. For each item present the analysis, planned
diff, test conditions and a commit message following the repository convention,
then ask 承認 / 修正依頼 / スキップ. For `needs-user-decision`, show competing
options with evidence and ask first. Only after approval: implement; pin changed
behavior with a test (reproducing test first for a bug); run the repository's
targeted checks and `git diff --check`; stage explicit paths only; commit that
item alone. `reject` and `already-satisfied` make no commit (a regression test
for `already-satisfied` is committed). If verification fails, stop that item,
report partial edits, and ask; never commit unverified work. Record per item:
commit hash, disposition, reply draft.

## Finalize

Show commits, each reply body preview (with its kind) and the threads to
resolve (ROLE bot or self, reply succeeded). Ask once: push + reply + resolve / push + reply only /
nothing. Never force-push.

- Push: require branch and HEAD unchanged; if the remote is ahead, show the
  commits and ask `pull --ff-only` (else merge, never rebase) or abort. Push by
  branch name, then fetch the tracking ref and require it to equal HEAD.
- Reply: write each body to a temp file with Write (never inline in the shell);
  post a thread reply with `gh api repos/{owner}/{repo}/pulls/{n}/comments/{rootId}/replies -X POST -F body=@file`.
  For a review body or issue comment, prepend the standalone reply reference
  header defined under `REPLY_PATH=standalone` in
  `pr_comment_implement/finalization.md` (the `> 返信対象: [...]({REPLY_REF_URL})`
  line plus the `> （@{login}）` line, with the item's `html_url` and author) and
  post with `gh api repos/{owner}/{repo}/issues/{n}/comments -X POST -F body=@file`.
  State what changed with the commit link, or why nothing changed with evidence.
  On failure ask retry or abort; do not fall back silently.
- Resolve: only for bot/self threads whose reply succeeded, via
  `resolveReviewThread(input:{threadId})`; verify `isResolved=true`. Review
  bodies and issue comments have no resolve state; report resolve as not
  applicable for them.
- PR body: after a verified push with at least one commit, follow
  "Offer a PR body update" in `pr_comment_implement/finalization.md` with
  PULL_NUMBER = the PR number and PR_BODY_DOCS = `ai/common/pr_body_core.md`
  and `pr_body_format.md`. A failure here keeps the push and replies.

Finish with a per-item table: kind / skipped / commit / reply / resolve, plus PR body
result. State that nothing is pushed if the user chose "nothing".
