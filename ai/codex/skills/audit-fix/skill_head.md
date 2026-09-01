---
name: audit-fix
description: >
  Apply the config-audit items decided 適用する: diffs mechanically, null-diff
  rewrites through design and implementation subagents. Accepts a platform key
  and an optional run directory; defaults to the newest Codex audit run.
---

Parse the arguments after the skill name: a token containing `/` is <RUN_DIR>; `claude`, `codex`, or `gemini` is <PLATFORM> (default `codex`). If <RUN_DIR> is absent, run `bash ~/.config/ai-pr/bin/ai_audit_run_dir.sh --latest <PLATFORM>` — it prints the newest run directory and never creates one.

For every user confirmation, ask the user directly and wait for the reply: resume-or-discard, the single selection confirmation, and each rolling design confirmation (承認 / 修正依頼 / スキップ). Present multi-choice sets as numbered lists and treat a number-only reply as that option.

Subagent launch: use the registered subagents `audit_fix_designer` and `audit_fix_implementer` — their role instructions and their reasoning effort are baked into their definitions, so pass only the payload each role defines. Designers and implementers alike parallelize up to the child-agent slots available at runtime; if they exceed the slots, use waves. Process each completed design as it returns; if the runtime surfaces results only per wave, degrade to wave-batch order. Subagents cannot spawn subagents (max_depth 1) — all orchestration stays in this session.
