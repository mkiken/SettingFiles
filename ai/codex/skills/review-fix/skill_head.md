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
