---
name: prompt-self-improvement
description: Improve Claude, Gemini, or Codex prompt configuration through evidence-based diagnosis, candidate prompt changes, evaluation design, and reviewable source edits. Use when the user asks to improve, audit, optimize, refactor, or make AI prompts, instructions, memories, skills, commands, agents, or AGENTS.md/GEMINI.md/CLAUDE.md behavior better.
---

# Prompt Self-Improvement

Use this skill to improve this repository's AI assistant prompts without letting them drift.

## Core rule

Treat self-improvement as an engineering loop, not as permission to rewrite instructions freely.

Only change persistent prompt sources after you have evidence, a clear target behavior, and a validation plan. If the user only asks for analysis, stop at a reviewable proposal.

## Source map

- Shared always-on behavior: `ai/common/prompt_base.md`
- Claude entrypoint: `ai/claude/_CLAUDE.md`
- Gemini entrypoint: `ai/gemini/_GEMINI.md`
- Codex source fragments: `ai/common/prompt_base.md`, `ai/common/characters/rikka_takanashi.md`, `ai/codex/codex_base.md`
- Codex generated file: `ai/codex/_AGENTS.md`; do not edit it directly
- Tool-specific workflows: `ai/*/skills/`, `ai/*/commands/`, `ai/*/agents/`
- Shared workflow skills: `ai/common/skills/`
- Sync scripts: `mac/initialization/ai/*.sh` and `mac/updates/*.sh`

## Improvement workflow

1. Identify the behavior to improve and the assistant(s) affected.
2. Read the relevant source files before proposing changes.
3. Gather evidence from user corrections, failed outputs, duplicated instructions, conflicts, stale docs, or repeated manual workflow.
4. Classify the fix:
   - Put short universal rules in `prompt_base.md`.
   - Put assistant-specific mechanics in that assistant's base file or entrypoint.
   - Put multi-step, task-specific procedures in a skill.
   - Put reusable invocations in commands.
   - Put deterministic lifecycle enforcement in hooks or settings.
   - Keep generated files generated.
5. Prefer the smallest change that fixes the demonstrated failure.
6. Remove or move noisy instructions instead of adding more rules when prompt size or conflicts are the real problem.
7. Validate with realistic prompts or scripts. For prompt behavior, include at least one ordinary case and one failure case that motivated the change.

## Guardrails

- Do not add instructions that let an assistant silently rewrite its own persistent prompts.
- Do not optimize based on a single anecdote unless the user explicitly wants that preference encoded.
- Do not merge Claude/Gemini/Codex rules when their tool behavior differs.
- Do not store long procedures in always-on prompt files.
- Do not weaken confirmation, cleanup, commit, or safety workflows while trying to reduce friction.
- Do not edit character files for workflow behavior unless the requested change is specifically about character voice.
- Do not cite volatile line numbers in prompt comments or documentation.

## Evaluation loop

When the user wants measurable optimization, use this sequence:

- Define success criteria before rewriting.
- Build a small eval set from real tasks and known failures.
- Score the current prompt as the baseline.
- Generate candidate prompt edits.
- Score candidates against the same evals and keep a holdout case for regression detection.
- Recommend the candidate only if it improves the target behavior without worsening core workflows.
- Ask for review before applying persistent changes unless the user has already requested implementation.

Research-style optimizers such as prompt improvers, OPRO, Promptbreeder, TextGrad, or DSPy are optional tools for larger eval-backed efforts. They are not a substitute for repository-specific evidence and manual review.

## Response format

For analysis-only work, return:

- Target behavior
- Evidence
- Diagnosis
- Proposed source changes
- Validation plan
- Risks

For implementation work, make the edits, regenerate derived files if needed, run validation, and report the changed sources plus test results.
