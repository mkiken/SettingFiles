---
name: pr-self-review
description: Review the current branch's PR, fix clear behavior-preserving issues, request approval for behavior changes, and pass remaining findings to the existing review HTML workflow. Use for an explicit self-review request.
---

# PR Self Review

Run once in the current terminal, using one reviewer, unless the arguments
start with `--from-run <RUN_DIR>` (see "Findings from a multi-AI run").
Additional request text is review emphasis, not permission to select another PR
or bypass approval. Calling this skill authorizes only the behavior-preserving
repairs below.

## Establish the target

Read the repository instructions before operating on it. Resolve the current
branch's PR with `gh pr view --json number,url,state,baseRefOid,headRefOid,headRefName`.
Require an attached branch matching headRefName, an OPEN PR, and empty
`git status --porcelain` including untracked files. With `--from-run`, validate
the input and apply the synchronization rule below before requiring HEAD
matching headRefOid. Otherwise require HEAD matching headRefOid at startup.
Stop with any failed condition; do not checkout, stash, commit or push to proceed.
Verify that the exact base commit is available; stop if it cannot be read.
Record the repository, branch, base and head OIDs for the entire run.

Resolve this skill directory's real path. Its grandparent is `ai/common`.
Read `pr_review_core.md` there for review scope, the seven Code Quality
Perspectives, existing-comment deduplication and line-number rules. Read
`pr_review_finding_format.md` for the result format. These are review criteria;
do not execute their output-file workflow or another PR review skill.
Read REVIEW.md at the recorded head if present and apply repository review
instructions. Inspect the full PR diff and line-numbered diff using the existing
`~/.config/ai-pr/bin/format_pr_diff_with_line_numbers.sh` helper. Fetch existing
comments with `~/.config/ai-pr/bin/fetch_existing_comments.sh`. Bound output and
keep scratch data outside the reviewed repository.

Trace changed behavior through callers, tests and relevant unchanged code.
Review all seven perspectives once. Skeptically verify each candidate against
primary code and tests inline; do not launch specialist or verifier agents.
Do not manufacture findings. Existing comments suppress duplicate reporting,
not repair of an actual unresolved defect.

## Address existing comments first

After establishing the target (and, for `--from-run`, validating and syncing
its input as described below), invoke `pr-comment-implement-batch-self` for the
same PR before reviewing. Follow its collection, classification, per-item and
finalization rules, including confirmations. If there are no eligible items,
continue without its skip or finalization prompts. Report skipped and unresolved
items, then continue; do not treat them as new findings merely because they remain.

If any comment repair is uncommitted or not pushed to the PR, stop and report
it; never review the older published snapshot as if it included the repair.
After the batch finishes, re-run Establish the target and record the current
base and head before review. Stop if the PR or branch changed, or the target
checks fail. For `--from-run`, compare the source SHA with this refreshed head
and apply the re-verification rules below before repairing imported findings.

## Fix failing CI before review

After existing comments and target refresh, inspect the PR checks for the recorded
head, including failure logs. If checks or relevant logs cannot be retrieved,
stop and report why. Report pending checks; do not wait for them at this stage.
If no checks have failed, continue to review.

Diagnose each failed check and repair it under the approval and verification
rules in "Repair findings". Ask the user when the cause or repair approach is
unclear. If any failure remains unresolved, verification fails, or required
approval is declined or unavailable, stop and report the state. Do not fix
unrelated pre-existing issues merely to clean up the repository.

For CI repairs, run "Confirm commit and push" before review. If the repairs
are not committed and pushed, stop and report them. Re-establish the target,
require the same PR and branch, and inspect the new head's checks. Wait for
checks corresponding to the repaired failures; proceed only when they pass.
If they fail, cannot be identified, or their status cannot be retrieved, stop
and report the evidence. For `--from-run`, compare its source SHA against this
new head and apply the re-verification rules below.

## Findings from a multi-AI run

With `--from-run <RUN_DIR>`, read the single full SHA in `<RUN_DIR>/self_fix`
and the non-empty results among `claude.md`, `gemini.md`, and `codex.md`.
Stop before synchronization if the marker is missing or invalid, a result is
unreadable, or there are no non-empty results. If the SHA differs from the
current PR head, require the resolved RUN_DIR to be a run under the resolved
directory returned by the existing `ai_review_pr_dir <PR_NUMBER>` helper from
`ai_review_run_dir.sh`. This verifies that the run belongs to the current
repository and PR. Stop if ownership cannot be verified.

If local HEAD differs from the PR head, fetch `refs/pull/<PR_NUMBER>/head` from
`origin`. Require `FETCH_HEAD` to equal the headRefOid returned by GitHub and
require that local HEAD is an ancestor of that exact SHA. Immediately before
`git merge --ff-only <verified-sha>`, confirm the recorded branch, local HEAD,
and clean status still match. Afterward, re-check that the branch, local HEAD and
clean status match the target and that the PR is still open with the same head.
Stop on a failed check, a failed Git operation, or a local HEAD that is ahead
or diverged. Record the verified current base and head for the review.

After addressing existing comments and refreshing the target, skip the one-reviewer review stage. Read each result, merge duplicates across
AIs, and verify every imported finding inline before repairing. If the SHA matches
the PR head, a finding you judge false stays a remaining finding and only completed
repairs leave the remaining set. If the SHA differs, re-verify every imported
finding against the recorded head's code, callers, tests and PR diff. Use
`git diff --no-color <base>...<head>` and render it with the existing diff helper's
`--stdin` option so locations come from the recorded commits. Feed findings
that still hold into "Repair findings", report resolved
findings with evidence, and report unverifiable findings in the conversation.
Before repairing on the new snapshot, confirm that the local branch and HEAD
and the published PR head still match the recorded values. Continue with the
existing repair and commit/push approval rules.

## Repair findings

Automatically repair only PR-introduced issues for which all of these hold:
explicit repository rules or existing contracts prove the issue; the solution
is unambiguous and local; behavior is unchanged; and targeted checks can verify
it. General bad-practice labels and confidence scores alone are insufficient.
Preserve repository approval requirements, including destructive actions,
public API changes, dependency additions, weakened validation and persistent
prompt changes. Do not expand into unrelated pre-existing cleanup.

For EVERY behavior change, including an obvious bug fix, present the proposed
patch, before/after behavior, affected callers, planned test conditions and
expected results. Obtain per-item approval using the platform's permitted user
confirmation mechanism BEFORE editing. If behavior preservation is uncertain,
require approval too. Unresolved specification or design choices need discussion
rather than a guessed fix. Deferred or rejected repairs remain findings.

After approval of a bug fix, establish a reproducing test before fixing it.
Run repository-required targeted checks for every repair and inspect its callers
and affected paths again. Do not rerun the whole PR review. If verification
fails or a new design choice appears, stop repairing that item, retain an
accurate account of partial edits and failures, and ask for the needed decision.
Never mark a failed or unverified repair complete. Preserve unrelated edits
that appear during the run; do not reset or restore files to discard them.

In the conversation, list each repair's repository-relative file:line, change,
evidence and verification result. Distinguish automatic repairs from approved
behavior changes. Do not put completed repairs into the HTML findings or a
separate fix-state database.

## Confirm commit and push

When the repairs left any uncommitted change, run this before the handoff; with
no repair, skip it. Never skip it as "review-only work": the repairs are
deliverable changes. Run task-completion's Post-Implementation Workflow
(commit and push / commit only / leave uncommitted, with its staging and
hunk-check rules): show the repaired files, a commit message following the
repository convention, the branch, push remote and destination. Stage only this
run's repaired paths explicitly, commit once, never force-push. For a push,
fetch first and stop with the ahead/behind counts if the remote is ahead; after
pushing, require the PR headRefOid to equal the local HEAD. Never commit or push
without the user's choice.

## Hand off to the existing review workflow

Re-read the PR head and local branch/HEAD before handoff. Expect the recorded
values, or the commit made in "Confirm commit and push" as local HEAD (and as PR
head after a push). Anything else is drift: stop and report it rather than
handing off stale findings. Confirm each remaining finding still exists after
the local repairs. Anchor findings to the PR head at handoff: after a push,
regenerate the line-numbered diff for the new head and map findings onto it; with
no push, keep the recorded PR head and its original line-numbered diff, because
a commit absent from GitHub cannot back links, excerpts or review-post anchors.
If a location cannot be mapped honestly, report it in the conversation as
needing verification instead of inventing an HTML anchor. Without a push,
explain in the conversation that HTML code excerpts are the published PR
snapshot, while the repairs are still local.

For `--from-run`, before creating the new run, raise `AI_REVIEW_KEEP_RUNS` for
that invocation if the normal pruning would remove the source run.
Use the existing `ai_review_run_dir.sh <PR_NUMBER>` helper to create a run.
Its resolved run directory is the authorized output target for this invocation.
Save only the remaining findings in the shared result format as `claude.md`
when running Claude or `codex.md` when running Codex. Write the no-findings
result even when every issue was repaired or no issue was found. Do not include
repair logs or extra commentary in this review result file.

With `--from-run`, write each AI's remaining findings into a file under its
original name. Omit completed repairs.
If the reviewed SHA differed, map each remaining finding to the verified path
and lines of the published PR head at handoff, retaining source attribution.
Report unmappable findings in the conversation. Renumber retained findings
sequentially, keep the skipped existing-comment section, and write the
no-findings result when none remain. Leave the original RUN_DIR unchanged.

Invoke the existing `review-merge` skill with that exact run directory. This is
aggregation, not a second review. It alone owns merging, HTML rendering, server
startup verification, opening, carryover and follow-up guidance. Do not copy
those procedures here or create merged.json or browser-owned state.json yourself.
Use the existing review-consider, review-fix and review-post skills for subsequent
HTML decisions; do not add a self-review-specific continuation or state format.
If handoff fails, report the preserved run path and failure without claiming the
HTML opened. Never commit or push implicitly to make the local repairs match
GitHub; only "Confirm commit and push" may do so.
