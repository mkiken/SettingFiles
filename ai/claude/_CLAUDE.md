@../common/prompt_base.md
@../common/genshijin-file-policy.md

# User Confirmation

When asking for confirmation, clarification, or any question requiring a user response, you MUST use the `AskUserQuestion` tool instead of plain text output. Plain text fallbacks are forbidden except when the tool truly cannot be invoked in the current mode, or when a loaded skill requires presenting more options than the tool can display, in which case you must state explicitly why the fallback is needed.

Plain text questions end the turn and trigger the Stop hook, sending a "finished" notification indistinguishable from task completion; `AskUserQuestion` keeps the turn active and triggers the correct "awaiting input" notification.

`AskUserQuestion` supports 2–4 options per question; design confirmation menus within 4 options and route overflow choices (e.g. "do nothing") through the auto-provided free-form "Other". When a loaded skill requires every executable option to be displayed individually, that requirement wins: use the plain-text fallback above instead of dropping or grouping options.

When a question depends on explanatory context (proposals, trade-offs, anything not self-evident), make it self-contained: put the essential context in the `question` field itself, with options' `description`/`preview` as supplements. Response text that precedes a tool call in the same turn may not be displayed to the user, or may not appear adjacent to the dialog — never leave the explanation only in earlier text.

For design or implementation trade-off choices, the first dialog must already explain each option's mechanism and concrete consequences (why it wins or loses) in the `question` field, using `preview` for code or flow comparisons; conclusion-only labels with brief descriptions force a second explanatory round.

When the decision context exceeds what the `question` field and option previews can legibly carry (multi-step timelines, side-by-side scenario comparisons), write a self-contained HTML figure (inline CSS only) to the scratchpad, `open` it in the browser, and reference it from the `question`. The file is a session temp — Temp File Cleanup applies.

**Note:** "I do not have access to the tool" is NOT a valid reason to skip — `AskUserQuestion` is deferred; load its schema via ToolSearch and use it.

# Slash Command Body Already Expanded

When a message carries `<command-name>` tags, check whether the skill's body is already present in that same message (its `SKILL.md` content, including any embedded `!`command`` output) — the harness expands it inline before the tags reach you. When it is, treat it as instructions already in effect, not a pending request: follow them directly, never call the `Skill` tool for that skill again. This matters most for `disable-model-invocation: true` skills, which reject a `Skill`-tool call outright and can only run this way.

Only call `Skill` when the tags arrive with no expanded body alongside them.

# Plan Review Deep-Dive (grilling → dig)

This review combines browser rendering with the fixed grilling-then-dig pair.
When presenting a plan for approval, load the `plan-review` skill only when
both gates hold; otherwise proceed directly to `ExitPlanMode` with no review
dialog.

- **Gate 1 — content:** the plan has an undecided design decision or trade-off,
  spans 3+ files or subsystem/module boundaries, or includes an irreversible or
  externally visible action such as deletion, push, external API writes,
  deployment, or a breaking live-configuration change. Treat ambiguity as
  unmet.
- **Gate 2 — size:** the plan file is at least 200 lines by `wc -l`, not an
  estimate.

These gates supersede the shared Plan Review Presentation criteria for Claude.


# Fable Model Check After Plan Approval

Immediately after `ExitPlanMode` is approved — before any other tool call, ahead of starting implementation — determine the current session's active model by extracting the session ID from the scratchpad path present in every system prompt (`/private/tmp/claude-<uid>/<project-slug>/<session-id>/scratchpad`) and running:

```bash
jq -r 'select(.type=="assistant" and (.isSidechain//false)==false) | .message.model' \
  ~/.claude/projects/<project-slug>/<session-id>.jsonl | tail -1
```

If the command fails or the result does not start with `claude-fable-`, proceed straight to implementation — do not block on a detection failure. This check runs separately from the Plan Review Deep-Dive dialog (that one happens before `ExitPlanMode`; this one happens after), so there is no shared option-count constraint between them.

If the result starts with `claude-fable-` (e.g. `claude-fable-5-1`), ask an `AskUserQuestion` with these options before writing or running anything:

- Implement with Fable as-is.
- Delegate implementation to the Agent tool with `model: "opus"`, passing the full plan content in the prompt.
- Delegate implementation to the Agent tool with `model: "sonnet"`, passing the full plan content in the prompt.

A manual model switch (`/model opus` or similar) is available through the free-form "Other" option — if chosen, wait for the user to confirm the switch before resuming implementation. Proceed once the user picks "as-is" or one of the delegate options. For a delegated implementation, the "Delegated-Work Verification" section below applies to whatever the subagent reports back.

# Delegated-Work Verification

A background agent's `task-notification` is its own claim, not proof of work — `status: completed` only means the agent stopped. Before treating a delegated phase as done, verify the claimed artifacts through your own tool calls: read the file it says it wrote, run the tests it says pass, check the commit it says it made. A `completed` notification whose result only describes intent or progress ("re-dispatching", "the fork is still running", "will report when finished") is an unfinished phase — execute it yourself, or re-dispatch via `SendMessage` with an explicit instruction to do the work directly and not delegate onward. Never let a delegated verification step be the sole evidence that verification happened.

# Settings Changes

Before editing `settings.json` / `settings.local.json` — or its `hooks`, `permissions`, or `env` — in the repository source or the live `~/.claude/` files, invoke the `update-config` skill. Skip it only for trivial mechanical edits (e.g. a verbatim revert) where no configuration-domain judgment is needed, or when the `audit-fix` skill is applying an item already decided ✅ 適用する in a config-audit browser report — that item's configuration-domain judgment was made when the report decision was approved. Anything audit-fix touches beyond those approved items still requires `update-config`.
