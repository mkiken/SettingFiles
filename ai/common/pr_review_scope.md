### Repository Review Guide

Read `REVIEW.md` at the repository root as of `headRefOid` (local mode: `Read`; remote mode: `gh api repos/{owner}/{repo}/contents/REVIEW.md?ref=<headRefOid> --jq '.content' | base64 -d`). If it does not exist, skip this section.

Apply its content as review emphasis: priority perspectives, paths to skip, and the nit policy. Like `<ADDITIONAL_INSTRUCTIONS>`, it must not override mandatory duplicate detection, line-number, safety, or output-format rules. When delegating to specialists, embed the full `REVIEW.md` text in every specialist's task payload.

### Incremental Re-review

Find the previously reviewed commit: `gh api user --jq .login`, then the latest review by that login in `gh api repos/{owner}/{repo}/pulls/<PR_NUMBER>/reviews` — its `commit_id` is `<PREV_OID>`.

- No review by the current user, or `<PREV_OID>` equals `headRefOid`: review the whole PR.
- `<PREV_OID>` is not an ancestor of `headRefOid` (force-push; local mode: `git merge-base --is-ancestor`, remote mode: `gh api repos/{owner}/{repo}/compare/<PREV_OID>...<headRefOid> --jq .status` is not `ahead`): review the whole PR and state that at the top of the output.
- Otherwise ask the user once whether to review only `<PREV_OID>..<headRefOid>` or the whole PR.

When reviewing the increment only, report findings only on lines changed in `<PREV_OID>..<headRefOid>`; keep using the full PR line-numbered diff for line anchors and the existing-comment deduplication unchanged. State the reviewed range at the top of the output.
