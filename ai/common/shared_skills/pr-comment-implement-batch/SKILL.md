---
name: pr-comment-implement-batch
description: Handle all unresolved review threads of the current branch's PR in one run - choose threads to skip, then commit and reply per thread, and resolve bot/self threads. Use for an explicit batch PR-comment request.
---

# PR Comment Implement (Batch)

Run once in the current terminal on the current branch (no worktree). Additional
request text is emphasis only, never permission to select another PR or skip an
approval. Handles only unresolved review threads; issue comments and review
summaries have no resolve state and are out of scope.

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

## Collect threads

Query GraphQL `reviewThreads(first:100)` with `id isResolved isOutdated path
line comments(first:100){nodes{databaseId author{login __typename} body
createdAt url}}`. Keep only `isResolved=false`. If more than 100 threads exist,
say the list is truncated and handle what was fetched.

ROLE of a thread = its root comment author: `bot` when `__typename` is `Bot`
or the login ends with `[bot]`; else `self` when it equals
`gh api user --jq .login`; else `other` (bot wins over self).

## Skip selection

Before anything else, list threads as `n. [path:line] @author (role, outdated,
already-replied-by-me) summary`. Ask which numbers to skip (none / numbers) via
the platform's user-confirmation mechanism. Skipped threads are untouched. Stop
if none remain.

## Choose flow

If every remaining thread is a small, local fix with no open design decision,
recommend Inline; otherwise recommend Subagents. Let the user choose.

- Inline: the main session performs the Analyst brief per thread, in order.
- Subagents: one read-only subagent per thread, launched together (Claude: Task
  general-purpose; Codex: spawn). Prompt in a few lines: read this SKILL.md's
  "Analyst brief" and follow it; payload = full thread text, ROLE, repo, PR
  number, head OID. Subagents never edit, commit or post.

## Analyst brief

Read the complete thread, the affected code, callers and closest tests. Apply
the disposition rules from analysis-design.md. Return: disposition, evidence
inspected, files to change, change plan, test conditions with expected results.
Edit nothing.

## Per-thread loop

Strictly serial, in list order. For each thread present the analysis, planned
diff, test conditions and a commit message following the repository convention,
then ask 承認 / 修正依頼 / スキップ. For `needs-user-decision`, show competing
options with evidence and ask first. Only after approval: implement; pin changed
behavior with a test (reproducing test first for a bug); run the repository's
targeted checks and `git diff --check`; stage explicit paths only; commit that
thread alone. `reject` and `already-satisfied` make no commit (a regression test
for `already-satisfied` is committed). If verification fails, stop that thread,
report partial edits, and ask; never commit unverified work. Record per thread:
commit hash, disposition, reply draft.

## Finalize

Show commits, each reply body preview and the threads to resolve (ROLE bot or
self, reply succeeded). Ask once: push + reply + resolve / push + reply only /
nothing. Never force-push.

- Push: require branch and HEAD unchanged; if the remote is ahead, show the
  commits and ask `pull --ff-only` (else merge, never rebase) or abort. Push by
  branch name, then fetch the tracking ref and require it to equal HEAD.
- Reply: write each body to a temp file with Write (never inline in the shell);
  post with `gh api repos/{owner}/{repo}/pulls/{n}/comments/{rootId}/replies -X POST -F body=@file`.
  State what changed with the commit link, or why nothing changed with evidence.
  On failure ask retry or abort; do not fall back silently.
- Resolve: only for bot/self threads whose reply succeeded, via
  `resolveReviewThread(input:{threadId})`; verify `isResolved=true`.
- PR body: after a verified push with at least one commit, follow
  "Offer a PR body update" in `pr_comment_implement/finalization.md` with
  PULL_NUMBER = the PR number and PR_BODY_DOCS = `ai/common/pr_body_core.md`
  and `pr_body_format.md`. A failure here keeps the push and replies.

Finish with a per-thread table: skipped / commit / reply / resolve, plus PR body
result. State that nothing is pushed if the user chose "nothing".
