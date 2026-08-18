---
name: review-fix
description: >
  Fix adopted merged-review items in the working tree. Accepts a run directory
  and item numbers; defaults to the current branch's latest PR run.
---

Parse the arguments after the skill name: a token containing `/` is <RUN_DIR>; numeric tokens (space/comma separated) are <ITEM_NUMBERS>. If <RUN_DIR> is absent, resolve the current branch's PR via `gh pr view --json number --jq .number` and run `bash ~/.config/ai-pr/bin/ai_review_run_dir.sh --latest <PR_NUMBER>`.

For every user confirmation (initial selection, resume-or-discard, each rolling design confirmation — 承認 / 修正依頼 / スキップ), ask the user directly and wait for the reply.

Subagent launch: use the registered subagents `review_fix_designer` and `review_fix_implementer` — their role instructions are baked into their definitions, so pass only the payload each role defines. Designers: parallelize up to the child-agent slots available at runtime; if groups exceed the slots, use waves. Process each completed design as it returns; if the runtime surfaces results only per wave, degrade to wave-batch order (confirm each finished design sequentially, still implementing serially). Implementations: at most one at a time. Subagents cannot spawn subagents (max_depth 1) — all orchestration stays in this session.
