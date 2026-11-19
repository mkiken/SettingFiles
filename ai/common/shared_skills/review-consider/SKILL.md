---
name: review-consider
description: Discuss merged PR review findings marked for AI consideration, implement approved fixes in parallel worktrees, and post approved comments. Accepts an optional run directory; defaults to the current PR's latest run.
---

# Review Consider

Respond in Japanese. The optional first argument is the run directory. If absent, resolve the current branch's PR via `gh pr view --json number --jq .number`, then run `bash ~/.config/ai-pr/bin/ai_review_run_dir.sh --latest <PR_NUMBER>`. Resolve the run directory to an absolute path. Do not accept item numbers.

Read `merged.json` and browser-owned `state.json`; use merged.json `pr_number` as <PR_NUMBER>. Require schema version 2, exact item ID agreement, decisions from `fix`, `post`, `consider`, `dismiss`, or null, and string notes when present. Select only items with `decision: "consider"`; use their optional `note`. If none are selected, report that and stop. Invalid or missing state stops the workflow; ask the user to save the report again. Never write `state.json` or `merged.json`.

Determine ownership once per session: compare merged.json `pr_author` with `gh api user --jq .login`. Equal means `own`, different means `others`. If either value cannot be obtained, ask the user once whether this is their own PR and use the answer. For `others`, never recommend or offer `fix`: present only `post` or `dismiss`, and switch an item to the existing fix flow only when the user explicitly asks for a fix.

Read `consider/consider_state.json` if present. Require schema version 1, matching resolved `run_dir`, a `head_ref_oid` matching merged.json, and item keys drawn from merged.json. Read the current PR head with `gh pr view <PR_NUMBER> --json headRefOid --jq .headRefOid`; if it cannot be obtained, stop. A current head that differs from `checked_head_oid` (the last verified head; use `head_ref_oid` when absent) is not a stop condition: run **Head drift** below. If the file is otherwise invalid, stop and ask for a new review run; never overwrite existing results. Validate each existing item: status is draft or approved, rationale and policy are nonempty strings, post_body is null or a string, and optional action is null, fix, post or dismiss. Invalid fields stop without overwriting results. Preserve all existing items on updates.

## Rolling consideration

Resolve this installed skill directory to its real path; read `references/considerer.md` beside it for the research role. Read the current platform's `review-fix/SKILL.md` and its **Incremental considered fixes** entry for implementation and integration; use `review-post/SKILL.md` for posting. Keep this parent session as the sole orchestrator throughout, rather than launching a second orchestration session.

At startup require an attached calling branch whose HEAD equals the reviewed PR head, unless resuming this run's recorded local merges; for `others`, defer this requirement to the first explicitly requested fix. Record the invoking repository, branch and expected parent OID in fix_state via the incremental entry. Require the reviewed Git object to be locally readable. Research always uses the immutable snapshot `checked_head_oid` through `git show <checked_head_oid>:<path>` and `git grep <pattern> <checked_head_oid> -- <paths>`, never mutable calling-worktree files. Before accepting a result, starting implementation, merging, posting or final push, verify the public PR head still equals `checked_head_oid` and the calling branch/HEAD matches the recorded expected parent OID; if the PR head moved, run **Head drift**. Stop affected work on an unverifiable head or an unexplained calling HEAD change; preserve results and worktrees.

Launch one research subagent per pending item: Claude uses its available general-purpose agent tool; Codex uses `spawn_agent` with the default role and `fork_turns: "none"` so research does not inherit the full conversation. Pass only the absolute role path, repository path, RUN_DIR, item id, note, ownership (`own` or `others`), reviewed head OID and output path `consider/item-<id>.md`. Use available child slots, filling them as tasks finish; approved implementations share those slots with remaining research. Do not make workers spawn more agents. If the runtime cannot expose individual completions, process each completed wave without claiming live completion order. If delegation is unavailable, report the limitation instead of silently researching everything in the parent.

Handle results in completion order. Read only the completed item's detail, verify its evidence against the snapshot, and present validity, alternatives, recommended action, policy and impact; for fixes include files and test conditions with expected outcomes, and for posts show the exact full proposed finding body. Ask for missing information and do not rush agreement. Only one user confirmation may be pending. While discussing one item, other research and implementation may continue. Never dump every worker's detailed report into the conversation.

Record reasoning and policy as `draft`. Obtain explicit per-item approval of the final action (`fix`, `post`, or `dismiss`), policy, and exact posting text when applicable. Set `approved` only after that confirmation. A changed action, policy or posting text returns the item to `draft` until confirmed again. Previously approved items without action need that decision before execution. A fix approval immediately feeds its design to **Incremental considered fixes**, even for one item; do not wait for all research. Post approvals queue for one final posting pass; dismiss approvals need no implementation. A failed worker leaves its item unresolved with the failure reported, never implicitly approved.

Only the parent writes shared state and performs mutating Git/GitHub operations. Researchers write only their assigned report, implementers only their assigned worktree. Never edit the calling worktree as an inline shortcut.

Write `consider/consider_state.json` with this shape, retaining other items:

```json
{
  "schema_version": 1,
  "run_dir": "/absolute/run/path",
  "head_ref_oid": "reviewed PR head SHA",
  "checked_head_oid": "last verified PR head SHA",
  "items": {
    "1": {"status": "draft", "rationale": "evidence and trade-offs", "policy": "proposed or agreed policy", "post_body": null, "action": null}
  }
}
```

`head_ref_oid` stays the review-time head (carryover matches it against merged.json); `checked_head_oid` is optional and advances only through **Head drift**. `status` is `draft` or `approved`; `rationale` and `policy` are strings; `post_body` is null or the agreed finding body string, without attribution or carryover suffixes. `action` is optional for backward compatibility and is null or `fix`, `post`, `dismiss`; a missing action is unresolved for execution. Preserve existing items and validate the complete JSON before atomic replacement.

## Head drift

Run this when the PR head differs from `checked_head_oid`, instead of stopping:

1. `git fetch`, then require the calling worktree clean; if dirty, stop and report the paths.
2. Bring the calling branch up to the PR head: `git merge --ff-only` when its HEAD is an ancestor, otherwise `git merge` (this run's local merges diverged from the remote). Never rebase, which would invalidate recorded group commit OIDs. Use the repository's merge-commit convention. On conflict, run `git merge --abort`, preserve results and worktrees, and stop with the conflicted paths.
3. Record the post-merge HEAD as fix_state's `expected_parent_oid`; this is an explained change. Any other calling HEAD change stays a stop.
4. List files changed by `git diff --name-only <old checked_head_oid> <new PR head>`. Re-verify only unmerged items (unresearched, draft, approved or implementing) whose item paths or designed `## Files to edit` intersect that list; keep the rest unchanged. Merged items are not re-verified.
5. Launch the researcher in re-verification mode (see `references/considerer.md`) with the old and new head OIDs. It reports `resolved` or `remains` with evidence.
6. `remains`: continue. Return an approved item whose rationale, policy or design changed to `draft` for renewed confirmation; implementing worktrees meet the new HEAD through the normal merge and conflict flow.
7. `resolved`: tell the user the problem is already gone with evidence (commit or `file:line`) and ask whether to skip it, one confirmation at a time. On skip, record `action: dismiss`, `status: approved` and the resolving commit in rationale; otherwise continue ordinary consideration.
8. Set `checked_head_oid` to the new PR head, validate the complete JSON, and replace atomically.

## Finish

Continue rolling implementation and local merges until research, decisions and fix groups are resolved or explicitly deferred. Post all approved `post` ids together through review-post, using explicit item numbers to override HTML selection; no HTML reselection or save is required. Revalidate approved bodies and the remote head against `checked_head_oid` immediately before posting, running **Head drift** if it moved. Preserve attribution, anchoring, exceptional confirmations, and independent verification. A posting failure or uncertain outcome blocks final push until resolved or the user explicitly defers that item; do not retry blindly.

Run the repository's required checks on the integrated branch. If local merges exist, show the integrated commits and verification results, then ask `pushする` / `pushしない` once. Push only on explicit approval, using worktree-task's **Finish the selected merge action** push checks, and independently verify remote ref and upstream. Recheck the remote head against `checked_head_oid` immediately before pushing (run **Head drift** if it moved, then show the new commits before asking again); a final push ends this snapshot's workflow. Evaluate review-fix's PR body update flow only after verified push success, once for the combined changes. Report per-item outcomes, retained worktrees, failures and whether push occurred.
