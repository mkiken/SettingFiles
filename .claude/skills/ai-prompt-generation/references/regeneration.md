# Regenerate AI Prompts

Canonical source-to-command mapping for regenerating committed outputs. The full init scripts (`mac/initialization/ai/{claude,gemini,codex}.sh`) cover everything; the targeted commands below are faster.

| Edited source | Regenerate with |
| --- | --- |
| `ai/common/prompt_base.md` (Claude/Gemini load it at runtime via `@file`) | Codex only: `zsh -c 'source mac/scripts/common.sh && generate_codex_agents'` |
| `ai/common/genshijin-activate.md` (upstream-synced by `sync_genshijin_rule`; keep local edits out of it — put overrides in `genshijin-file-policy.md`), `ai/common/genshijin-file-policy.md` | None — loaded at runtime via `@file` by Claude/Gemini only; Codex does not consume them |
| `ai/codex/codex_base.md` | `zsh -c 'source mac/scripts/common.sh && generate_codex_agents'` |
| Shared-core skill sources (`ai/common/*_core.md`, `ai/{codex,gemini}/skills/*/skill_head.md`/`skill_tail.md`; includes pr-review-subagents skill adapters) | `zsh -c 'source mac/scripts/common.sh && verify_ai_skill_generation_idempotency'` |
| pr-reviewer agent sources (`ai/common/pr_review_subagents/intro_*.md`, `ai/common/pr_review_subagents/format_*.md`, `ai/*/agents_src/`) | `zsh -c 'source mac/scripts/common.sh && generate_pr_reviewer_agents <platform>'` |
| pr-review verifier sources (`ai/common/pr_review_subagents/verifier_core.md`, `ai/*/agents_src/pr_review_verify/`) | `zsh -c 'source mac/scripts/common.sh && verify_pr_review_verifier_agent_generation_idempotency'` (regenerates and verifies) |
| config-audit auditor sources (`ai/common/config_audit_subagents/`, `ai/*/agents_src/config_audit/`) | `generate_config_auditor_agents <platform>` from `mac/scripts/common.sh` |
| review-fix subagent sources (`ai/common/review_fix_subagents/`, `ai/codex/agents_src/review_fix/`) | `zsh -c 'source mac/scripts/common.sh && verify_review_fix_agent_generation_idempotency'` (regenerates and verifies) |
| audit-fix subagent sources (`ai/common/audit_fix_subagents/`, `ai/*/agents_src/audit_fix/`) | `zsh -c 'source mac/scripts/common.sh && verify_audit_fix_agent_generation_idempotency'` (regenerates and verifies all three platforms) |
