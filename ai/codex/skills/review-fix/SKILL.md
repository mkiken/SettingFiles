---
name: review-fix
description: >
  Fix adopted review items from a merge run directory in the working tree.
  Use this skill when the user wants to fix, apply, or implement merged
  review findings in the working tree, or says things like "指摘を直して",
  "採用した指摘を修正して", "fix the review items". Accepts an optional run
  directory and item numbers; if none is given, detects the latest run for
  the current branch's PR automatically and uses state.json's adopted items.
---

Parse the arguments after the skill name: a token containing `/` is <RUN_DIR>; numeric tokens (space/comma separated) are <ITEM_NUMBERS>. If <RUN_DIR> is absent, resolve the current branch's PR via `gh pr view --json number --jq .number` and run `bash ~/.config/ai-pr/bin/ai_review_run_dir.sh --latest <PR_NUMBER>`.

For the pre-edit confirmation, ask the user directly and wait for the reply.

Fix selected review items from a merge run directory in the current working tree. Respond in Japanese.

## Inputs

- <RUN_DIR>: run directory containing `merged.json` (see adapter for resolution).
- <ITEM_NUMBERS>: optional space- or comma-separated item ids, overriding state.json.

## Item Selection

1. Read `<RUN_DIR>/merged.json`. `items[].id` are the serial numbers — never renumber.
2. If <ITEM_NUMBERS> is non-empty, select those ids. Otherwise read `<RUN_DIR>/state.json` (`items` is an object keyed by id string with `{"reviewed": bool, "adopt": bool}`) and select ids with `adopt: true`. If state.json is missing and no numbers were given, list the available items and ask the user which ids to fix.
3. If a selected id has no matching item, stop and report the mismatch instead of guessing.

## Workflow

1. Present the selected items (`id. [file:line_spec] priority | area: summary`) and confirm with the user before editing anything.
2. Fix the items one by one. For each item: read the file and enough surrounding context, use every source's detail text as guidance, apply the fix. If the finding looks wrong, already fixed, or the fix is genuinely ambiguous, skip it and record the reason — never guess.
3. After all items, run the repository's relevant tests (follow the project's documented test command).
4. Final summary in Japanese: per item — 修正済み (what changed, files touched) or スキップ (why); then `git diff --stat` output. Do not commit — leave the commit decision to the session's normal workflow.
