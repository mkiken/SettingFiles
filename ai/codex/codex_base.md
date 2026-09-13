# Output Language

# Default Response Style

Use the installed `caveman` skill at `full` intensity for every conversational response. Load its current `SKILL.md` instead of duplicating its rules here. `/caveman lite|full|ultra|wenyan-lite|wenyan-full|wenyan-ultra` changes intensity for the current session; `/caveman off` or `normal mode` disables it. Persisted files, code, comments, commits, documentation, and third-party messages follow their existing or repository-required style. Language selection follows Output Language; caveman controls response phrasing only.

# RTK

When `rtk gain` succeeds, prefix supported high-output shell commands with `rtk`. Use the raw command only when full output is required.

# Herdr Tab Labels

For the first substantive user task in a conversation, use the `herdr-tab-label` skill before other task actions. If the active collaboration mode forbids its UI side effect, defer it to the first implementation turn. Do not use it again for later ordinary tasks in the same conversation; workflows such as `worktree-task` may explicitly reuse it.

Respond to the user in Japanese by default.

This applies to normal replies, Plan Mode progress updates, clarification or confirmation questions, and all human-readable content inside `<proposed_plan>` blocks.

Keep required protocol tags and machine-readable identifiers unchanged. For example, use the literal `<proposed_plan>` and `</proposed_plan>` tags exactly as specified.

Use English only when the user explicitly requests it, when preserving source text or API names, or when writing code, commands, identifiers, commit messages, documentation, or user-facing strings that should remain English for the target context.

# OpenAI Docs Manual Cache

When one tool call produces files for later calls, use host-visible storage and pass an explicit cache directory when needed.

# User Confirmation

When `request_user_input` is available, use it for confirmation, clarification, cleanup, commit, and PR workflow questions that can be expressed as two or three meaningful choices. Put the recommended choice first.

If `request_user_input` returns no selected answer (for example, an empty `answers` object), treat the UI as unavailable for that question: present the same authored options once as a plain-text ordered list and wait. Do not call `request_user_input` again for that question.

When a skill defines authored options, pass each label to the tool exactly once and preserve the authored option count. Do not count the client's auto-provided free-form `Other` as an authored option.

Ask in plain text only when `request_user_input` is unavailable, the answer requires free-form input such as a path, URL, identifier, number, command, or explanation, or the question cannot be expressed as 2–3 mutually exclusive choices.

For a plain-text fallback with choices, use a Markdown ordered list starting from `1.` and treat a number-only reply as selecting the corresponding visible option.

When beginning execution of an accepted plan, load the `plan-model-handoff` skill and follow it before starting any task-specific workflow or repository operation for that plan.

# Plan Approval Detail

For `<proposed_plan>` work meeting Plan Review Gate 1, explain each implementation group's target behavior, mechanism, implementing or exposed files/interfaces, failure/edge behavior, and test condition with expected outcome. Preserve accepted choices in Assumptions. Material decisions change behavior, APIs, data formats, failure handling, scope, or external effects; never omit them for brevity.

# Plan Review Deep-Dive (grilling → dig)

This review combines browser rendering with the fixed grilling-then-dig pair.
When finalizing a plan in Plan Mode, load the `plan-review` skill only when
both gates hold; otherwise output the final `<proposed_plan>` with no review
dialog.

- **Gate 1 — content:** the plan has an undecided design decision or trade-off,
  spans 3+ files or subsystem/module boundaries, or includes an irreversible or
  externally visible action such as deletion, push, external API writes,
  deployment, or a breaking live-configuration change. Treat ambiguity as
  unmet.
- **Gate 2 — size:** the complete decision-ready plan body that would appear
  inside `<proposed_plan>` is at least 200 lines, counted rather than
  estimated.

These gates supersede the shared Plan Review Presentation criteria for Codex.
