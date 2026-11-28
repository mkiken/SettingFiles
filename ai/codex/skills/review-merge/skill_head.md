---
name: review-merge
description: >
  Merge multi-AI PR review results into merged.json and an HTML report. Accepts
  a run directory; defaults to the current branch's latest PR run.
---

Parse the arguments after the skill name: the first token, if present, is <RUN_DIR>. If absent, resolve the current branch's PR via `gh pr view --json number --jq .number` and run `bash ~/.config/ai-pr/bin/ai_review_run_dir.sh --latest <PR_NUMBER>` to get <RUN_DIR>.

Before rendering, compare every `sources[].text` in `merged.json` against its original finding, including all indented detail and proposed fixes through the separator. Confirm each finding appears exactly once; repair any missing or truncated text and repeat the comparison before proceeding.
