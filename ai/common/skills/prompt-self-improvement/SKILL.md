---
name: prompt-self-improvement
description: Improve AI prompt configuration with evidence-based diagnosis; also loaded when surfacing Opportunistic Improvement Proposals.
---

# Prompt Self-Improvement

Improve this repository's AI assistant prompts without letting them drift.

## Core rule

Self-improvement is an engineering loop, not license to rewrite instructions freely. Change persistent prompt sources only with evidence, a clear target behavior, and a validation plan. If the user asks only for analysis, stop at a reviewable proposal.

## Source map

- Shared always-on behavior: `ai/common/prompt_base.md`
- Claude entrypoint: `ai/claude/_CLAUDE.md`
- Gemini entrypoint: `ai/gemini/_GEMINI.md`
- Codex source fragments: `ai/common/prompt_base.md`, `ai/common/characters/nyaruko.md`, `ai/codex/codex_base.md`
- Codex generated file: `ai/codex/_AGENTS.md`; do not edit it directly
- Tool-specific workflows: `ai/*/skills/`, `ai/*/commands/`, `ai/*/agents/`
- Shared workflow skills: `ai/common/skills/`
- Shared-core generation sources: `ai/common/*_core.md` plus platform adapters (`skill_head.md`/`skill_tail.md`) and `ai/*/agents_src/`; generated outputs (Codex/Gemini generated `SKILL.md`, pr-reviewer agents, `_AGENTS.md`) are never edited directly — regenerate per the "Regenerate AI Prompts" table in the repository `CLAUDE.md`
- Sync scripts: `mac/initialization/ai/*.sh` and `mac/updates/*.sh`

## Improvement workflow

1. Identify the behavior to improve and the affected assistant(s).
2. Read the relevant source files before proposing changes.
3. Gather evidence: user corrections, failed outputs, duplicated instructions, conflicts, stale docs, repeated manual workflow.
4. Classify the fix: short universal rules → `prompt_base.md`; assistant-specific mechanics → that assistant's base file or entrypoint; multi-step task-specific procedures → a skill; reusable invocations → commands; deterministic lifecycle enforcement → hooks or settings; generated files stay generated.
5. Prefer the smallest change that fixes the demonstrated failure; write new or edited prompt text as concisely as meaning and intent allow — loaded prompts consume context.
6. When prompt size or conflicts are the real problem, remove or move noisy instructions instead of adding rules. For "shorten without changing meaning" tasks, follow `ai/common/prompt_shortening_guide.md`.
7. Validate with realistic prompts or scripts; for prompt behavior include at least one ordinary case and one failure case that motivated the change.
8. If triggered by the Opportunistic Improvement Proposals rule rather than an explicit user request, stop at the analysis-only Response format and follow the proposal ordering and timing rules defined there.

## Guardrails

- No instructions letting an assistant silently rewrite its own persistent prompts.
- No optimizing from a single anecdote unless the user explicitly wants that preference encoded.
- No merging Claude/Gemini/Codex rules when their tool behavior differs.
- No long procedures in always-on prompt files.
- No weakening confirmation, cleanup, commit, or safety workflows to reduce friction.
- No editing character files for workflow behavior unless the change is specifically about character voice.
- No volatile line numbers in prompt comments or documentation.
- No changes that broaden your own automatic activation surface (skill descriptions, trigger keywords, hook matchers) unless the user explicitly asks.

## Evaluation loop

For measurable optimization: define success criteria before rewriting; build a small eval set from real tasks and known failures; score the current prompt as baseline; generate candidate edits; score candidates on the same evals, keeping a holdout case for regression detection; recommend a candidate only if it improves the target behavior without worsening core workflows; ask for review before applying persistent changes unless the user already requested implementation.

External prompt optimizers are optional for larger eval-backed efforts — not substitutes for repository-specific evidence and manual review.

## Response format

For analysis-only work, return:

- Background — plain-language narrative for a reader with no session context: for OIP-triggered proposals, which "When to propose" criterion matched and the concrete session events that triggered it (what happened, when); for explicit user requests, the request and what prompted it
- Target behavior
- Evidence
- Diagnosis
- Proposed source changes
- Validation plan
- Risks
- Affected assistants (Claude / Gemini / Codex); for changes to generated-output sources, name the required regeneration command (see the "Regenerate AI Prompts" table in the repository `CLAUDE.md`)

For implementation work: make the edits, regenerate derived files if needed, run validation, and report the changed sources plus test results.

## Presenting proposals for approval

The proposal block always follows the task's fully displayed deliverable output (e.g. review results), never precedes it.

When asking approval (mid-session or at the Completion-Time Check), print each proposal's full analysis — Background, Target behavior, Evidence, Diagnosis, Proposed source changes, Affected assistants — as plain response text immediately before the confirmation tool call, nothing in between. Re-print it there even if already shown earlier: text preceding a tool call may not be displayed, or may not appear adjacent to the dialog.

For the same reason each question must be self-contained: the `question` field itself carries a condensed Background — the matched trigger criterion, the concrete session events, and which file gets what change (3-5 sentences) — so the user can decide from the dialog alone. A bare "add X?" is never sufficient; option labels and descriptions are supplements, not a substitute for the analysis.
