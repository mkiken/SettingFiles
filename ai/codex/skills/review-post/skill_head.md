---
name: review-post
description: >
  Post adopted merged-review items to a GitHub PR as review comments. Accepts
  a run directory and item numbers; defaults to the current branch's latest PR run.
---

Parse the arguments after the skill name: a token containing `/` is <RUN_DIR>; numeric tokens (space/comma separated) are <ITEM_NUMBERS>. If <RUN_DIR> is absent, resolve the current branch's PR via `gh pr view --json number --jq .number` and run `bash ~/.config/ai-pr/bin/ai_review_run_dir.sh --latest <PR_NUMBER>`.

`{ai_header}` = `🤖 **AI コードレビュー**` — this run merges findings from several AIs, so the header never names the posting AI.

For the final posting confirmation, ask the user directly and wait for the reply.
