---
name: review-merge
description: >
  Merge multi-AI PR review result files into merged.json and an HTML report.
  Use this skill when the user wants to merge, consolidate, or de-duplicate
  PR review findings from multiple AIs (Claude/Gemini/Codex) into one report,
  or says things like "レビュー結果をマージして", "merge the review results",
  "レポートを作って". Accepts an optional run directory; if none is given,
  detects the latest run for the current branch's PR automatically.
---

Parse the arguments after the skill name: the first token, if present, is <RUN_DIR>. If absent, resolve the current branch's PR via `gh pr view --json number --jq .number` and run `bash ~/.config/ai-pr/bin/ai_review_run_dir.sh --latest <PR_NUMBER>` to get <RUN_DIR>.
