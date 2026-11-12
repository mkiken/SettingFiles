---
name: pr-self-review
description: Review the current branch's PR, fix clear behavior-preserving issues, request approval for behavior changes, and pass remaining findings to the existing review HTML workflow. Use for an explicit self-review request.
---

# PR Self Review

Run once in the current terminal, using one reviewer. Additional request text
is review emphasis, not permission to select another PR or bypass approval.
Calling this skill authorizes only the behavior-preserving repairs below.

## Establish the target

Read the repository instructions before operating on it. Resolve the current
branch's PR with `gh pr view --json number,url,state,baseRefOid,headRefOid,headRefName`.
Require an attached branch matching headRefName, HEAD matching headRefOid, an
OPEN PR, and empty `git status --porcelain` including untracked files. Otherwise
stop with the failed condition; do not checkout, stash, commit or push to proceed.
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
behavior changes. State that changes remain uncommitted and unpushed. Do not
put completed repairs into the HTML findings or a separate fix-state database.

## Hand off to the existing review workflow

Re-read the PR head and local branch/HEAD before handoff. If they differ from
the recorded values, stop and report the drift rather than handing off stale
findings. Confirm each remaining finding still exists after the local repairs.
Anchor findings to the recorded PR head using the original line-numbered diff;
map moved lines back to that revision. If a location cannot be mapped honestly,
report it in the conversation as needing verification instead of inventing an
HTML anchor. Explain in the conversation that HTML code excerpts are the
published PR snapshot, while repairs are still local.

Use the existing `ai_review_run_dir.sh <PR_NUMBER>` helper to create a run.
Its resolved run directory is the authorized output target for this invocation.
Save only the remaining findings in the shared result format as `claude.md`
when running Claude or `codex.md` when running Codex. Write the no-findings
result even when every issue was repaired or no issue was found. Do not include
repair logs or extra commentary in this review result file.

Invoke the existing `review-merge` skill with that exact run directory. This is
aggregation, not a second review. It alone owns merging, HTML rendering, server
startup verification, opening, carryover and follow-up guidance. Do not copy
those procedures here or create merged.json or browser-owned state.json yourself.
Use the existing review-consider, review-fix and review-post skills for subsequent
HTML decisions; do not add a self-review-specific continuation or state format.
If handoff fails, report the preserved run path and failure without claiming the
HTML opened. Follow the enclosing task-completion/commit approval workflow;
never commit or push implicitly to make the local repairs match GitHub.
