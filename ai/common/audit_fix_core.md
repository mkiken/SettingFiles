Apply the audit items decided ✅ 適用する in an audit run directory. Respond in Japanese.

## Inputs

- <RUN_DIR>: run directory containing `audit.json` and `state.json` (see adapter for resolution).

Item selection comes only from `state.json` — never ask the user for item numbers, and never accept
them as arguments. The browser report is the sole decision surface.

## Item Selection

1. Read `<RUN_DIR>/audit.json`. `items[].id` are the serial numbers — never renumber.
2. Read `<RUN_DIR>/state.json`. If it is missing, tell the user to decide the items in the browser and
   stop; reopening is the **zsh shell function** `audit-report <platform_key>`, not a skill.
   Never fall back to asking for item numbers in the conversation.
3. Reject a `schema_version` other than 1, reject ids absent from `audit.json`, and require the key set
   to match `audit.json`'s items exactly. Each item's `decision` is `"apply"` (✅ 適用する),
   `"dismiss"` (🚫 対応しない), or `null` (未判断).
4. Select ids whose `decision` is `"apply"`. For each, every id in its `depends_on` closure must also be
   `"apply"`; otherwise stop and report the pair. Never widen the selection yourself — the report
   already enforces this, so a violation here means a hand-edited state file.
5. Zero selected → report it and stop without writing anything.
6. Never write `<RUN_DIR>/state.json` — the browser owns it.

## Routing: mechanical vs designed

Route each selected item on its `diff`:

- non-null unified diff → **Mechanical Track**
- `null` (config-audit builds diffs only for deletions, ambiguity rewrites, and shortenings, so these
  are the conflict resolutions) → **Design Track**

An item belongs to exactly one track, with one exception: when a `depends_on` closure spans both
tracks, the whole closure goes to the Design Track. Applying one half mechanically while the other
half is still being designed re-introduces the very problem the pair was recorded for.

## Grouping

Compute each item's target file set from `targets[].file` — not from `file` alone, which only mirrors
`targets[0]`. `overlap` and `conflict` items cite two locations and may edit either, so grouping on
`file` would let two groups edit one file concurrently.

A group is a connected component over shared target files: union-merge items whose target file sets
intersect, and always keep a `depends_on` closure in one group. Number groups `g1..gN` by the
first-appearance order of their lowest item id. A group is mechanical when every item in it has a
diff, and a design group when any item lacks one.

## Order of the two tracks

Run every mechanical group to completion **before** starting the Design Track. Mechanical application
depends on each item's `quote` matching byte for byte, and a rewrite that touches another part of the
same file invalidates those anchors. Grouping keeps target files disjoint, but a design's
`## Files to edit` may add a file a mechanical group also edits, so the ordering is the only guarantee.

## apply_state.json

Durable per-item and per-group outcome record at `<RUN_DIR>/apply_state.json`.

```json
{
  "schema_version": 1,
  "run_dir": "/abs/path/to/run",
  "selected_ids": [1, 4, 7],
  "groups": {
    "g1": {
      "track": "mechanical",
      "files": ["~/.claude/CLAUDE.md"],
      "item_ids": [1, 4],
      "status": "applied",
      "design_file": null,
      "reason": null,
      "updated_at": "2026-09-01T11:30:00+09:00"
    },
    "g2": {
      "track": "design",
      "files": ["ai/common/prompt_base.md", "ai/claude/_CLAUDE.md"],
      "item_ids": [7],
      "status": "designed",
      "design_file": "fix/design-g2-prompt_base.md.md",
      "reason": null,
      "updated_at": "2026-09-01T11:34:00+09:00"
    }
  },
  "items": {
    "1": {"group": "g1", "status": "applied", "reason": null},
    "4": {"group": "g1", "status": "skipped", "reason": "quote mismatch"}
  }
}
```

Group status: `pending|designing|designed|approved|waiting|implementing|applied|skipped|failed`; the
design lifecycle values apply to design groups only. Item status: `pending|applied|skipped|failed`;
`reason` is required for `skipped` and `failed`. `files` for a design group is copied from its design
file's `## Files to edit` once the design completes.

The Design Track updates this file at every status transition and re-reads it before every transition
and after any interruption or context compaction — never trust memory. The Mechanical Track writes it
once at the end with terminal statuses only. Never write `<RUN_DIR>/state.json` — the browser owns it.

If `apply_state.json` already exists with any non-terminal group, ask the user: resume (keep it; skip
groups already terminal) or discard and start over. If every group is already terminal, start over
without asking.

## Selection Confirmation

Present the selected items grouped by group — `g<N> [files] 機械適用|設計` followed by each
`id. [file > section] category | summary`. Before the existing single yes/no confirmation, re-list only
the selected items whose `risk` is an object as `#id summary — reason`. If a selected item omits `risk`,
warn that it is risk未評価; never infer that it is safe. This is warning-only: do not dismiss, block, or
ask an additional confirmation because of risk. This is yes/no, not item numbers. Apply file changes
only after this approval.

## Mechanical Application

1. Order each group's items by target file, then apply from the bottom up — by descending position of
   the item's `quote` within that file — so earlier edits do not invalidate later anchors.
2. Before each edit, verify the item's `quote` still matches the file byte for byte. On mismatch, skip
   that item with status `skipped` and reason `quote mismatch`, and report it — never apply the diff to
   a guessed location.
3. Apply the item's `diff`. A diff that does not apply cleanly → `failed` with the reason; never
   hand-repair the hunk.
4. If any member of an item's `depends_on` closure was skipped or failed, do not apply the rest of that
   closure either — mark them `skipped` with that reason. Applying one half alone re-introduces or
   worsens the other half's problem, which is exactly what the dependency records.
5. Group → `applied` when every item applied, `skipped` when every item was skipped, `failed` otherwise.

## Design Flow

Phases: Setup → Design (parallel) → Rolling Confirmation → Implementation (parallel) → Finish. There
are no worktrees, no commits, and no merges: the audited files include paths outside any repository
(`~/.claude/CLAUDE.md`, `~/.codex/config.toml`), so a worktree cannot hold the whole target set.
Subagents never write under `<RUN_DIR>` except the designer's own design file. Large content moves
through files under `<RUN_DIR>/fix/`, never through conversation text.

### Setup

Create `<RUN_DIR>/fix/` if missing, and initialize or resume `apply_state.json` per the rules above.

### Design Phase (parallel)

Spawn one design subagent per design group, all in parallel (the adapter defines the launch primitive
and slot limit). Payload per designer: <RUN_DIR>, group id, the group's target files, item ids (the
designer reads `audit.json` itself for detail), output path
`<RUN_DIR>/fix/design-<group>-<basename>.md`, and on a redesign round the user's feedback. Designers
return only a 1-2 line Japanese summary; all detail lives in the design file. Set the group `designing`.

### Rolling Confirmation

As each design completes — do not wait for the rest — set the group `designed`, read the design file's
`## Files to edit` yourself, record it as the group's `files`, and present the returned summary plus
that file list to the user: approve / request changes / skip. Request changes → back to `designing`;
respawn the designer with the feedback in the payload. Skip → group and its items `skipped` with the
reason. Approve → the overlap check below.

### Implementation (parallel)

On approval, compare the group's `files` against the `files` of every group that is `approved`,
`waiting`, or `implementing`.

- No overlap → launch the implementer and set `implementing`.
- Overlap → set `waiting`; start it only after every overlapping predecessor reaches a terminal state.

Without worktrees this overlap rule is the only thing preventing two implementers from editing one
file, so never launch an overlapping pair concurrently. Implementer payload: <RUN_DIR>, group id,
design file path. Implementers read neither `audit.json` nor `state.json`. When one finishes, set the
group `applied` (or `failed` with the reason) and summarize its reply.

### Finish

When every group is terminal, print a Japanese summary: per item — 適用済み (what changed, files
touched) / スキップ (why) / 失敗 (why); per group — its track and outcome. Then `git diff --stat` for
repository-tracked files, and separately list every edited path that is not tracked (`~/.claude/…` and
friends never appear in `git diff`). Do not commit — leave the commit decision to the session's normal
workflow.
