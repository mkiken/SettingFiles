# Output Language

# Default Response Style

Use the installed `caveman` skill at `full` intensity for every conversational response. Load its current `SKILL.md` instead of duplicating its rules here. `/caveman lite|full|ultra|wenyan-lite|wenyan-full|wenyan-ultra` changes intensity for the current session; `/caveman off` or `normal mode` disables it. Persisted files, code, comments, commits, documentation, and third-party messages follow their existing or repository-required style. Language selection follows Output Language; caveman controls response phrasing only.

# RTK

When `rtk gain` succeeds, prefix supported high-output shell commands with `rtk`. Use the raw command only when full output is required.

# Combined Tool Output

When combining results from multiple tool calls, bound their total output, not just each result. If required content is truncated, retrieve the missing content before editing.

# Herdr Tab Labels

For the first substantive user task in a conversation, use the `herdr-tab-label` skill before other task actions. If the active collaboration mode forbids its UI side effect, defer it to the first implementation turn. Do not use it again for later ordinary tasks in the same conversation; workflows such as `worktree-task` may explicitly reuse it.

Respond to the user in Japanese by default.

This applies to normal replies, Plan Mode progress updates, clarification or confirmation questions, and all human-readable content inside `<proposed_plan>` blocks.

Keep required protocol tags and machine-readable identifiers unchanged. For example, use the literal `<proposed_plan>` and `</proposed_plan>` tags exactly as specified.

Use English only when the user explicitly requests it, when preserving source text or API names, or when writing code, commands, identifiers, commit messages, documentation, or user-facing strings that should remain English for the target context.

# OpenAI Docs Manual Cache

When one tool call produces files for later calls, use host-visible storage and pass an explicit cache directory when needed.

# User Confirmation

For every required user confirmation or decision (approval, clarification with choices, cleanup, commit, or PR workflow), use a choice UI whenever a callable, permitted tool can present all options in one question. Do not replace a usable choice UI with a prose question. This governs presentation, not when confirmation is required; do not reconfirm already-authorized work.

Prefer `request_user_input`; do not automatically switch to `request_user_input_async`. Follow the active runtime's mode and purpose restrictions; never override its permission restrictions.

Preserve every skill-authored choice's wording, order, and meaning. Always display explicit numbers starting at 1; keep an existing numbering prefix rather than duplicating it. For two or three choices, present all choices as numbered UI labels. For four or more choices, put the complete numbered list in the question text, expose only the first two choices as numbered UI labels, and instruct the user to enter any choice number in the client's auto-provided free-form `Other`. Do not add a custom free-input choice or count or rename `Other` as an authored choice. Never omit a choice from the complete list or split the decision across questions.

Interpret a number-only reply, including text entered in `Other`, against the complete authored list. The UI position of `Other` does not select authored choice 3. Empty, out-of-range, multiple-number, or ambiguous answers require clarification before action; preserve explicit free-form routes defined by the skill. If `request_user_input` is unavailable or not permitted for the purpose, use a numbered plain-text list and accept number-only replies.

An async acknowledgement only means the question was accepted; wait for the user's answer before dependent work. Do not duplicate a pending question. Empty responses and missing selections are not approval. Never treat an unanswered approval request as approval.

When the answer inherently needs free-form input (a path, URL, identifier, or explanation), keep it free-form; do not invent choices.

# Plan Model Handoff

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
