---
name: review-post
description: >
  Post adopted review items from a merge run directory to the PR as review
  comments. Use this skill when the user wants to post, submit, or upload
  merged review findings to a GitHub PR, or says things like "レビューを投稿して",
  "採用した指摘をコメントして", "post the review". Accepts an optional run
  directory and item numbers; if none is given, detects the latest run for
  the current branch's PR automatically and uses state.json's adopted items.
---

Parse the arguments after the skill name: a token containing `/` is <RUN_DIR>; numeric tokens (space/comma separated) are <ITEM_NUMBERS>. If <RUN_DIR> is absent, resolve the current branch's PR via `gh pr view --json number --jq .number` and run `bash ~/.config/ai-pr/bin/ai_review_run_dir.sh --latest <PR_NUMBER>`.

`{ai_header}` = `🤖 **AI コードレビュー**` — this run merges findings from several AIs, so the header never names the posting AI.

For the final posting confirmation, ask the user directly and wait for the reply.
