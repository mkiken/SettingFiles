Fix selected review items from a merge run directory in the current working tree. Respond in Japanese.

## Inputs

- <RUN_DIR>: run directory containing `merged.json` (see adapter for resolution).
- <ITEM_NUMBERS>: optional space- or comma-separated item ids, overriding state.json.

## Item Selection

1. Read `<RUN_DIR>/merged.json`. `items[].id` are the serial numbers — never renumber.
2. If <ITEM_NUMBERS> is non-empty, select those ids. Otherwise read `<RUN_DIR>/state.json` and select by its `schema_version`: `2` → `items` is keyed by id string with `{"decision": "fix"|"post"|"dismiss"|null}`; select ids whose `decision` is `"fix"`. `1` (legacy) → `items` values are `{"reviewed": bool, "adopt": bool}`; select ids with `adopt: true`. Any other `schema_version` → stop and report it. If state.json is missing and no numbers were given, list the available items and ask the user which ids to fix.
3. If a selected id has no matching item, stop and report the mismatch instead of guessing.

## Grouping and Mode Selection

Group the selected items by their `file` field; items whose `area`/`summary` clearly share one root cause may be merged into one group. Number groups `g1..gN` in first-appearance order.

Present the selected items (`id. [file:line_spec] priority | area: summary`) with their grouping and confirm with the user before editing anything. Then: 1 group → Inline Flow; 2+ groups → Subagent Flow.

## fix_state.json

Durable per-item outcome record, read by the next run's review-merge for carryover; keep outcomes and reasons accurate. Subagent Flow updates it immediately at every status transition and re-reads it before every transition and after any interruption or context compaction — never trust memory. Inline Flow writes it once at the end, with terminal statuses only.

Group status: `designing|designed|approved|waiting|implementing|implemented|committed|fixed|skipped|rejected`. `waiting` means the design is approved but a still-unmerged group edits an overlapping file; `implemented` means the implementer finished and the commit/merge confirmation is pending; `committed` means the user chose commit-only, so the task worktree and branch survive; `fixed` means the group's commit is merged into the calling branch (or, for `commit_only`, committed).

Item status stays `pending|fixed|skipped|rejected` — review-merge's carryover reads it. Mark items `fixed` when the group reaches `fixed` or `committed`, and `skipped` with a reason when the user chooses `no_commit`.

```json
{
  "schema_version": 2,
  "run_dir": "/abs/path/to/run/",
  "base_branch": "feature/example",
  "base_oid": "<calling worktree HEAD at Setup>",
  "selected_ids": [3, 5, 7],
  "groups": {
    "g1": {
      "file": "src/auth.ts",
      "item_ids": [3, 5],
      "status": "implementing",
      "design_file": "fix/design-g1-auth.ts.md",
      "files": ["src/auth.ts", "tests/auth.test.ts"],
      "worktree": {
        "path": "/abs/path/to/task-worktree",
        "branch": "task/review-fix-g1-20260726T101200",
        "created_from_oid": "<base OID this worktree branched from>"
      },
      "commit_oid": null,
      "merge_action": null,
      "reason": null,
      "updated_at": "2026-07-26T10:12:00+09:00"
    }
  },
  "items": {
    "3": { "group": "g1", "status": "fixed", "note": "null guard added" },
    "5": { "group": "g1", "status": "pending", "note": null }
  }
}
```

`files` is copied from the design file's `## Files to edit` once the design completes. `merge_action` is `commit_merge_push|commit_merge|commit_only|no_commit|null`. Inline Flow's single implicit group needs no `groups` entry, no `worktree`, and no base fields — write `schema_version: 2`, `run_dir`, `selected_ids`, and `items`.

## Inline Flow

1. Fix the items one by one. For each item: read the file and enough surrounding context, use every source's detail text as guidance, apply the fix. If the finding looks wrong, already fixed, or the fix is genuinely ambiguous, skip it and record the reason — never guess.
2. After all items, run the repository's relevant tests (follow the project's documented test command).
3. Write `<RUN_DIR>/fix/fix_state.json` per the schema above with the final per-item outcomes (terminal statuses only) — the next merge run reads it for carryover.
4. Final summary in Japanese: per item — 修正済み (what changed, files touched) or スキップ (why); then `git diff --stat` output. Do not commit — leave the commit decision to the session's normal workflow.

## Subagent Flow

Designers run in parallel and read-only; each approved group is implemented in its own task worktree, so implementers run in parallel too. Commit, merge, and every user confirmation stay in this orchestrator session — subagents never commit. Large content moves through files under `<RUN_DIR>/fix/`, never through conversation text. Never write `<RUN_DIR>/state.json` — the browser owns it.

Phases: Setup → Design (parallel) → Rolling Confirmation → Worktree Implementation (parallel) → Confirm & Merge (strictly serial) → Finish.

### Worktree mechanics come from worktree-task

Read <WORKTREE_TASK_DOC> (the adapter defines the path) before creating the first worktree and follow it by reference — do not restate its steps here. Apply these of its sections per group: *Record the original state*, *Create the task worktree*, *Handle any post-invocation failure*, *Confirm and create the commit*, *Require a clean invoking worktree before merging*, *Merge and verify cleanup*, *Handle other `wtm` failures*, *Handle merge conflicts*, and *Finish the selected merge action*.

Exceptions for this flow:

- Do not derive a slug via `herdr-tab-label` and do not set a tab label. The branch is `task/review-fix-<group>-<timestamp>` — apply worktree-task's uniqueness suffix rule if it already exists.
- *Preserve the workflow through plan mode* does not apply; this skill is already an approved, explicit invocation.
- Its four-choice commit confirmation is asked per group through this platform's confirmation mechanism (see the adapter).
- The commit is created by this session inside the task worktree, never by the implementer.

### Setup

Create `<RUN_DIR>/fix/` if missing. If `<RUN_DIR>/fix/fix_state.json` already exists with any non-terminal group, ask the user: resume (keep it; skip groups already terminal) or discard and start over. If every group is already terminal, start over without asking. Otherwise initialize it with every group `designing` and every item `pending`.

Then run worktree-task's *Record the original state* once for the whole flow: record the calling worktree's top-level path, its attached branch, and its exact `HEAD` OID, and verify `wtc`/`wtm` are available. Write the branch and OID to fix_state's `base_branch` / `base_oid`. A dirty calling worktree does not block design or implementation; the clean requirement applies per group at merge time.

### Design Phase (parallel)

Spawn one design subagent per group, all in parallel (the adapter defines the launch primitive and slot limit). Payload per designer: <RUN_DIR>, group id, group file, item ids (the designer reads merged.json itself for detail), output path `<RUN_DIR>/fix/design-<group>-<basename>.md`, and optional <CONSTRAINTS> containing accepted user decisions that are not in merged.json; on a redesign round, also include the user's feedback. Designers return only a 1-2 line Japanese summary; all detail lives in the design file.

### Rolling Confirmation

As each design completes — do not wait for the rest — set the group `designed`, read the design file's `## Files to edit` yourself, record it as the group's `files`, and present the returned summary plus that file list to the user: approve / request changes / skip. Request changes → back to `designing`; respawn the designer with the feedback in the payload. Skip → group and its items `skipped` with reason. Approve → the overlap check below.

### Worktree Implementation (parallel)

On approval, compare the group's `files` against the `files` of every group that is approved, `waiting`, `implementing`, `implemented`, or `committed` — i.e. every group whose edits are not yet merged into the calling branch.

- No overlap → create its task worktree immediately, based on the calling branch's *current* `HEAD` (re-read it; earlier merges have advanced it), record `worktree.path`/`branch`/`created_from_oid`, launch the implementer, and set `implementing`.
- Overlap → set `waiting`. Start it only after every overlapping predecessor reaches a terminal state, and only then create its worktree from the by-then updated base. This serializes overlapping groups; the implementer's "re-adapt to current code" rule absorbs the drift, and worktree-task's conflict handling is the last line of defence.

Implementer payload: <RUN_DIR>, group id, design file path, <WORKTREE_PATH>. When one finishes, set `implemented` and summarize its reply plus `git diff --stat` taken in that worktree by this session. Re-evaluate the `waiting` queue after every merge.

### Confirm & Merge (serial)

Handle finished groups in completion order, one at a time — never overlap two groups' commit/merge sequences, and never start the next before the current one reaches a terminal state.

Per group, follow worktree-task's *Confirm and create the commit*: ask its four choices, then for anything other than `コミットしない` stage only the design's `## Files to edit` paths explicitly inside the task worktree, verify the staged diff, commit with the repository's message convention, and record `commit_oid` and `merge_action`.

- Before merging, save the group's patch: `git diff <created_from_oid>..<commit_oid> -- <files>` into `<RUN_DIR>/fix/patch-<group>.diff`, so the group stays reverse-appliable as one unit after the merge.
- `commit_merge` / `commit_merge_push`: apply *Require a clean invoking worktree before merging* (a failure downgrades the group to `commit_only` semantics → `committed`), then *Merge and verify cleanup*, then the independent ancestor and cleanup checks. Success → `fixed`. Push only for `commit_merge_push`, via *Finish the selected merge action*.
- `commit_only` → `committed`; report the preserved worktree path, branch, and commit.
- `コミットしない` (`no_commit`) → group and its items `skipped` with the reason; report the preserved worktree, branch, and uncommitted changes.

Update fix_state.json at every transition and re-read it before each one — never trust memory.

### Finish

When every group is terminal (`fixed`/`committed`/`skipped`/`rejected`), run the repository's relevant tests once in the calling worktree. Final summary in Japanese: per item — 修正済み (what changed, files touched) or スキップ/却下 (why); per group — the merge outcome (マージ済み / コミットのみ + preserved branch and worktree path / 未コミット); then `git diff --stat` from the calling worktree.
