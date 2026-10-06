---
name: review-fix
description: >
  Fix merged-review items marked 修正する, each in its own task worktree. Accepts
  a run directory and item numbers; defaults to the current branch's latest PR run.
---

Parse the arguments after the skill name: a token containing `/` is <RUN_DIR>; numeric tokens (space/comma separated) are <ITEM_NUMBERS>. If <RUN_DIR> is absent, resolve the current branch's PR via `gh pr view --json number --jq .number` and run `bash ~/.config/ai-pr/bin/ai_review_run_dir.sh --latest <PR_NUMBER>`.

For every user confirmation, ask the user directly and wait for the reply: initial selection, resume-or-discard, each rolling design confirmation (承認 / 修正依頼 / スキップ), each group's four-choice commit/merge confirmation, the two-choice merge-conflict confirmation, and the PR body update confirmation. Present the four- and two-choice sets as numbered lists and treat a number-only reply as that option.

<WORKTREE_TASK_DOC> = `~/.codex/skills/worktree-task/SKILL.md`.

<PR_BODY_DOCS> = `~/.codex/skills/pr-body/SKILL.md`.

Subagent launch: use the registered subagents `review_fix_designer` and `review_fix_implementer` — their role instructions are baked into their definitions, so pass only the payload each role defines; the implementer payload includes <WORKTREE_PATH>. Designers and implementers alike parallelize up to the child-agent slots available at runtime; if they exceed the slots, use waves. Process each completed design as it returns; if the runtime surfaces results only per wave, degrade to wave-batch order. Confirm & Merge stays strictly serial regardless. The session running this skill owns orchestration, overlap checks, workflow state, and user confirmations. It may be the depth-1 lifecycle worker under `agents.max_depth = 2`; its designers and implementers must not spawn further agents. If that worker cannot surface a confirmation, relay the exact question and authored choices through the parent, wait for the user's answer, and resume only with that answer.
