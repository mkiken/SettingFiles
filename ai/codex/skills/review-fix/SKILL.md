---
name: review-fix
description: >
  Fix adopted review items from a merge run directory in the working tree,
  via parallel design subagents and serial implementation subagents.
  Use this skill when the user wants to fix, apply, or implement merged
  review findings in the working tree, or says things like "指摘を直して",
  "採用した指摘を修正して", "fix the review items". Accepts an optional run
  directory and item numbers; if none is given, detects the latest run for
  the current branch's PR automatically and uses state.json's adopted items.
---

Parse the arguments after the skill name: a token containing `/` is <RUN_DIR>; numeric tokens (space/comma separated) are <ITEM_NUMBERS>. If <RUN_DIR> is absent, resolve the current branch's PR via `gh pr view --json number --jq .number` and run `bash ~/.config/ai-pr/bin/ai_review_run_dir.sh --latest <PR_NUMBER>`.

For every user confirmation (initial selection, resume-or-discard, each rolling design confirmation — 承認 / 修正依頼 / スキップ), ask the user directly and wait for the reply.

Subagent launch: use the registered subagents `review_fix_designer` and `review_fix_implementer` — their role instructions are baked into their definitions, so pass only the payload each role defines. Designers: parallelize up to the child-agent slots available at runtime; if groups exceed the slots, use waves. Process each completed design as it returns; if the runtime surfaces results only per wave, degrade to wave-batch order (confirm each finished design sequentially, still implementing serially). Implementations: at most one at a time. Subagents cannot spawn subagents (max_depth 1) — all orchestration stays in this session.

Fix selected review items from a merge run directory in the current working tree. Respond in Japanese.

## Inputs

- <RUN_DIR>: run directory containing `merged.json` (see adapter for resolution).
- <ITEM_NUMBERS>: optional space- or comma-separated item ids, overriding state.json.

## Item Selection

1. Read `<RUN_DIR>/merged.json`. `items[].id` are the serial numbers — never renumber.
2. If <ITEM_NUMBERS> is non-empty, select those ids. Otherwise read `<RUN_DIR>/state.json` (`items` is an object keyed by id string with `{"reviewed": bool, "adopt": bool}`) and select ids with `adopt: true`. If state.json is missing and no numbers were given, list the available items and ask the user which ids to fix.
3. If a selected id has no matching item, stop and report the mismatch instead of guessing.

## Grouping and Mode Selection

Group the selected items by their `file` field; items whose `area`/`summary` clearly share one root cause may be merged into one group. Number groups `g1..gN` in first-appearance order.

Present the selected items (`id. [file:line_spec] priority | area: summary`) with their grouping and confirm with the user before editing anything. Then: 1 group → Inline Flow; 2+ groups → Subagent Flow.

## Inline Flow

1. Fix the items one by one. For each item: read the file and enough surrounding context, use every source's detail text as guidance, apply the fix. If the finding looks wrong, already fixed, or the fix is genuinely ambiguous, skip it and record the reason — never guess.
2. After all items, run the repository's relevant tests (follow the project's documented test command).
3. Final summary in Japanese: per item — 修正済み (what changed, files touched) or スキップ (why); then `git diff --stat` output. Do not commit — leave the commit decision to the session's normal workflow.

## Subagent Flow

Design subagents run in parallel; implementation subagents run strictly one at a time. Large content moves through files under `<RUN_DIR>/fix/`, never through conversation text. Never write `<RUN_DIR>/state.json` — the browser owns it.

### Setup

Create `<RUN_DIR>/fix/` if missing. If `<RUN_DIR>/fix/fix_state.json` already exists, ask the user: resume (keep it; skip groups already terminal) or discard and start over. Otherwise initialize it with every group `designing` and every item `pending`.

### fix_state.json

Single source of truth for flow state. Update it immediately at every status transition; re-read it before every transition and after any interruption or context compaction — never trust memory. It is also the durable per-item outcome record; keep outcomes and reasons accurate.

Group status: `designing|designed|approved|implementing|fixed|skipped|rejected`. Item status: `pending|fixed|skipped|rejected`.

```json
{
  "schema_version": 1,
  "run_dir": "/abs/path/to/run/",
  "selected_ids": [3, 5, 7],
  "groups": {
    "g1": {
      "file": "src/auth.ts",
      "item_ids": [3, 5],
      "status": "implementing",
      "design_file": "fix/design-g1-auth.ts.md",
      "files": ["src/auth.ts", "tests/auth.test.ts"],
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

`files` is copied from the design file's `## Files to edit` once the design completes.

### Design Phase (parallel)

Spawn one design subagent per group, all in parallel (the adapter defines the launch primitive and slot limit). Payload per designer: <RUN_DIR>, group id, group file, item ids (the designer reads merged.json itself for detail), output path `<RUN_DIR>/fix/design-<group>-<basename>.md`, and — on a redesign round — the user's feedback. Designers return only a 1-2 line Japanese summary; all detail lives in the design file.

### Rolling Confirmation

As each design completes — do not wait for the rest — set the group `designed`, read the design file's `## Files to edit` yourself, and present the returned summary plus that file list to the user: approve / request changes / skip. Approve → `approved`, append to the implementation queue. Request changes → back to `designing`; respawn the designer with the feedback in the payload. Skip → group and its items `skipped` with reason.

### Implementation Phase (serial)

Process the implementation queue in approval order with at most one implementation subagent running at a time (it may overlap with still-running designers and confirmations). Payload: <RUN_DIR>, group id, design file path. The implementer re-reads current code and adapts the design to it — earlier groups may have changed the tree. When it finishes: record per-item outcomes (`fixed`/`skipped` + note) in fix_state.json, save the group's patch with `git diff -- <files>` to `<RUN_DIR>/fix/patch-<group>.diff` (enables per-group reverse apply), then launch the next queued group.

### Finish

When every group is terminal (`fixed`/`skipped`/`rejected`), run the repository's relevant tests once in the main session. Final summary in Japanese: per item — 修正済み (what changed, files touched) or スキップ/却下 (why); then `git diff --stat` output. Do not commit — leave the commit decision to the session's normal workflow.
