---
name: pr-verify
description: Verify that an existing GitHub PR actually works in an isolated verification branch and worktree, after user approval of the verification design. Use for execution-based PR verification; ordinary code review belongs to pr-review.
---

# PR Verification

Invoke as `$pr-verify [PR number or URL] [verification focus]`. Without a PR,
resolve the current branch's PR with `gh pr view`; ask if it cannot be identified.
Use the platform's user-confirmation mechanism for every decision below.

## Inspect and propose

Read the target repository's AI instructions before working there. Record the
invoking worktree's path, branch (or detached state), exact HEAD, and status,
including untracked files. Preserve all pre-existing changes.

Resolve the PR repository, URL, state, base/head SHA and diff. Inspect changed
behavior, callers, existing tests, setup commands and external effects. Use
read-only GitHub access if the exact revisions are unavailable locally. Pin
findings to the recorded revisions rather than unrelated local changes.
If the PR is no longer open, ask whether to verify that snapshot before proceeding.

Present a verification design containing:

- The PR URL, pinned base/head SHA, scope and expected behavior.
- Cases with target, input, expected result, command, and proposed test code.
- Worktree path, verification branch, fixtures and temporary output locations.
- External effects, mock/log replacements, notification treatment and limitations.
- Any unresolved design decisions, with concrete alternatives and a recommendation.

Ask exactly:

1. `承認して進める`
2. `設計を修正する`
3. `中止する`

Wait for explicit approval before creating the worktree, writing verification
code, installing dependencies or executing the PR. Resolve uncertain decisions
with the user before dependent work. Changed scope, safety boundaries or test
design require renewed approval. In plan mode, present the design only; resume
this workflow after approval and after leaving plan mode.

## Isolate the approved snapshot

Before Git mutations, inspect configured hooks and checkout filters for external
effects, including worktree creation hooks. If their safety cannot be established,
stop and ask for a safe alternative before fetching or creating the worktree.

Fetch the recorded PR head and base from the PR's base repository using its PR
ref when needed (including fork PRs). Verify their object IDs against the recorded
SHAs; stop on mismatch rather than substituting a newer head. Do not checkout,
update, commit on, or merge into the original or PR branch.

Choose `verify/pr-<number>-<timestamp>`, appending a numeric suffix if occupied.
Confirm the branch and destination path do not already exist, then create:

```bash
git worktree add -b <verification-branch> <verification-path> <pinned-head-sha>
```

Independently inspect `git worktree list --porcelain`, the new worktree's branch,
HEAD and status. Require the expected path, branch, pinned HEAD and clean status.
On partial creation or failure, stop and report observed paths and refs; do not
force cleanup or reuse ambiguous state. Never stash, reset or clean the invoking
worktree to make verification possible.

All verification code, fixtures, fixes and generated files belong inside this
worktree. Save the approved design and results under `.pr-verify/<run-id>/`,
checking for existing files before writing. Keep credentials and real private
data out of files, logs and commits. Use synthetic fixtures.

## Execute safely

A worktree isolates files, not external effects. Before executing any setup,
hook, build, test or child process, trace its effects and apply the approved
replacements. Do not inherit live service credentials or configuration into a
test environment. Use temporary local data stores and worktree-local output.
Do not modify live dotfiles, shared databases, running services or system state.

Exercise the changed implementation itself. Mock the external write boundary,
not the behavior being verified. Replace sends, API writes, billing, deployment
and destructive operations with mocks or captured logs. Do not send real
notifications. For Slack or other notification payloads, disable user, group and
broadcast mentions and clearly label the content `テスト通知` (test notification),
even when captured by a mock or log. Neutralize mention markup as well as visible
mention text; do not claim actual notification delivery was verified.

Inspect commands before running them, including dependency lifecycle hooks.
If safe isolation cannot be established, do not execute that case: report it as
unverified with the reason and ask about a safe alternative when needed.
Stop immediately if an unexpected external effect or scope change is discovered.
Do not treat successful mocks as proof of live integration behavior.

Record expected and actual results, commands, exit codes, evidence, mock
boundaries and unverified cases. Separate baseline failures from PR regressions;
do not attribute a failure to the PR without evidence. At completion, re-read the
PR head: if changed, label the results as applying only to the pinned snapshot.
Do not silently rerun against the new head.

## When a defect is found

Stop execution, report the reproduction, evidence and proposed correction, then ask:

1. `修正まで行う`
2. `修正せず終了する`

The first choice authorizes preparing a fix design, not immediate editing.
Present that design and obtain approval before fixing and re-verifying only in
the verification worktree. Never transfer fixes to the original branch or PR.
The second choice proceeds to reporting and the preservation decision below.

## Report and preserve

Show the pinned SHA, case results, failures, mock coverage, unverified behavior
and report location. This workflow replaces ambient commit/push prompts with
the preservation and publication decisions below. Never push to the original
or PR branch, or merge verification changes into either branch.
Ask exactly:

1. `検証ブランチにローカルコミットして公開準備する`
2. `worktreeごと保持する`

Both choices retain the verification branch. For the second, report its path,
branch and uncommitted status and stop. For the first:

- Inspect repository hooks before committing; if they have unsafe effects,
  preserve state and ask for a safe alternative instead of running them.
- Recheck ownership, branch and changes. Stage explicit task-owned paths only,
  including the design, report and verification code. Inspect ignored artifacts
  for needed evidence; save a sanitized summary rather than committing secrets
  or dependency/build directories. Inspect the complete staged diff.
- Commit only on the verification branch, following repository conventions.
  Independently verify the commit, saved files and clean status, including
  untracked files. If saving fails or unexpected changes remain, preserve the
  worktree and stop. Never discard files to make cleanup pass.
- Keep the worktree until publication finishes. Local commit approval does not
  authorize pushing or updating the PR body.

## Prepare the PR verification section

Read the latest body from the original PR using its explicit repository and
number. Save it and the proposed complete body under the run directory. Use
`<!-- pr-verify:start -->` and `<!-- pr-verify:end -->` to delimit the managed
section. With no markers, append the section; with exactly one ordered pair,
replace only that section. Preserve all content outside the managed section.
Stop on incomplete, reversed or duplicate markers rather than guessing repairs.

Include execution time, run ID, PR URL, pinned base/head SHA, environment,
prerequisites, steps and commands. For each case, show expected and actual
results and status. Distinguish baseline failures, PR defects and results after
verification-only fixes. Include mock boundaries, unverified behavior and
remaining concerns. If the PR head advanced, state that the results apply only
to the pinned snapshot.

Link the report, verification code and sanitized logs using immutable URLs
containing the saved verification commit SHA, not branch-relative URLs. Include
available GitHub Actions run, Jenkins build/job and Slack notification links
whose relationship to this verification was confirmed. Identify a job-level
link when no specific build link is available. Mark unavailable evidence as
unavailable; never invent URLs or treat captured notifications as delivered.
Do not trigger jobs or send Slack messages to obtain links. Check both evidence
files and linked content for credentials or real private data before publication.

Show the proposed body and its actual diff, evidence files, destination
repository and verification branch. The destination is the PR's base repository;
inspect push hooks and workflows for effects such as CI and show those effects
before approval. If their safety is uncertain, stop and resolve it first.
Ask exactly:

1. `検証ブランチをpushしてPR本文を更新する`
2. `公開内容を修正する`
3. `公開せずローカル保存で終了する`

Wait for explicit publication approval. For revisions, regenerate the preview
and ask again. If declined, retain the local commit and worktree and report
their locations without publishing.

## Publish and verify

Immediately before pushing, resolve the current branch in the verification
worktree and require it to match the saved verification branch and commit.
Push that branch with `-u` to the approved base-repository remote without force.
Independently verify the remote ref matches the saved commit and the configured
upstream matches the pushed branch. On permission failure, stop rather than
choosing another repository. Do not update the PR body unless push is verified.

Re-read the PR body and head immediately before updating. If either changed
since the approved preview, rebuild against the latest body, update any stale
snapshot notice and obtain approval again. Use the exact approved file:

```bash
gh pr edit <PR-number> --repo <base-owner/repo> --body-file <approved-body-file>
```

Independently re-fetch the body and compare it with the approved file, allowing
only CRLF/LF and trailing-newline differences. A pre-write check cannot prevent
all concurrent edits; this post-write comparison is also required. On failure
or mismatch, stop without automatically retrying or reposting. Report which of
local saving, pushing and body updating succeeded or remain unconfirmed, and
retain the worktree. Never automatically delete published evidence on failure.

## Finish

After successful publication, ask exactly:

1. `worktreeを削除する`
2. `worktreeごと保持する`

For deletion, recheck ownership, branch, saved commit and clean status including
untracked files. From the invoking worktree, run
`git worktree remove <verification-path>` without force. Verify the worktree is
absent and the verification branch still points to the saved commit. Never
delete the verification branch or its remote ref. Preserve any unexpected or
failed cleanup state; never discard files to make cleanup pass.

Finally, independently recheck the invoking branch, HEAD and changes against the
recorded state; report differences without overwriting concurrent work. Report
the saved branch/commit, worktree disposition and how to resume with a new
worktree from that branch. Explain that re-verifying an updated PR requires a
fresh snapshot and design. Leave failed cleanup state intact and report it.
