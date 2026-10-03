---
name: ai-prompt-generation
description: Use when editing AI prompt sources or generated outputs in this repository — ai/common/ cores, ai/{claude,gemini,codex}/ skill adapters and agents_src/, generated SKILL.md / agent files, _CLAUDE.md / _GEMINI.md / _AGENTS.md composition, or the review-merge and config-audit report servers under shell/common/pr/.
---

# AI Prompt and Agent Generation

Read the reference that matches what you are touching.

- **Prompt composition, shared-core skills, generated subagents** — `_CLAUDE.md` / `_GEMINI.md` /
  `_AGENTS.md` composition, the per-skill core-file table, and the four generated subagent
  families (pr-review-subagents, config-audit, review-fix, audit-fix):
  `.claude/skills/ai-prompt-generation/references/generation.md`
  (`.agents/skills/ai-prompt-generation/references/generation.md`)
- **Regeneration commands** — the source-to-command table for regenerating committed outputs
  (`generate_codex_agents`, `verify_ai_skill_generation_idempotency`, the agent generators):
  `.claude/skills/ai-prompt-generation/references/regeneration.md`
  (`.agents/skills/ai-prompt-generation/references/regeneration.md`)
- **Report servers** — the `review-merge` / `config-audit` loopback HTML report flow, the shared
  `serve_review_report.py` profiles, and `state.json` ownership:
  `.claude/skills/ai-prompt-generation/references/report-servers.md`
  (`.agents/skills/ai-prompt-generation/references/report-servers.md`)
