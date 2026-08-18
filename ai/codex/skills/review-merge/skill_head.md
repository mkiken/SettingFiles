---
name: review-merge
description: >
  Merge multi-AI PR review results into merged.json and an HTML report. Accepts
  a run directory; defaults to the current branch's latest PR run.
---

Parse the arguments after the skill name: the first token, if present, is <RUN_DIR>. If absent, resolve the current branch's PR via `gh pr view --json number --jq .number` and run `bash ~/.config/ai-pr/bin/ai_review_run_dir.sh --latest <PR_NUMBER>` to get <RUN_DIR>.

For the report server, use `mcp__context_mode__ctx_execute` with `background: true` and a short timeout when that tool is available; run `serve_review_report.py` without `--open`. Its returned URL must be independently fetched before opening it once in the browser. If context-mode is unavailable, use the core fallback and still verify the server before one browser-open action.
