@../common/prompt_base.md
@../common/genshijin-file-policy.md

# User Confirmation

When asking for confirmation, clarification, or any question requiring a user response, you MUST use the `AskUserQuestion` tool instead of plain text output. Plain text fallbacks are forbidden except when the tool truly cannot be invoked in the current mode, in which case you must state explicitly why the fallback is needed.

Plain text questions end the turn and trigger the Stop hook, sending a "finished" notification indistinguishable from task completion; `AskUserQuestion` keeps the turn active and triggers the correct "awaiting input" notification.

`AskUserQuestion` supports 2–4 options per question; design confirmation menus within 4 options and route overflow choices (e.g. "do nothing") through the auto-provided free-form "Other".

When a question depends on explanatory context (proposals, trade-offs, anything not self-evident), make it self-contained: put the essential context in the `question` field itself, with options' `description`/`preview` as supplements. Response text that precedes a tool call in the same turn may not be displayed to the user, or may not appear adjacent to the dialog — never leave the explanation only in earlier text.

When the decision context exceeds what the `question` field and option previews can legibly carry (multi-step timelines, side-by-side scenario comparisons), write a self-contained HTML figure (inline CSS only) to the scratchpad, `open` it in the browser, and reference it from the `question`. The file is a session temp — Temp File Cleanup applies.

**Note:** "I do not have access to the tool" is NOT a valid reason to skip — `AskUserQuestion` is deferred; load its schema via ToolSearch and use it.

# Plan Review Deep-Dive (dig)

This section's skip criterion governs both the `dig` skill offer and the Plan Review Presentation browser offer — on Claude, that shared file's own line-count/format criteria do not apply; use this criterion for both instead. Its port-selection and launch mechanics still apply when the browser is actually opened.

When presenting a plan artifact for review, offer both — but first skip both for trivially mechanical plans: renames, bulk replacements, reverts, single-file fixes with no design decision, or plans whose every task is a stated verbatim edit. For those, skip straight to `ExitPlanMode` with no dialog.

Otherwise, merge this with the Plan Review Presentation offer into a single `AskUserQuestion` dialog (single-select, no multiSelect) with exactly three fixed options:

- Both: open the browser and also run dig.
- Open the browser now, decide on dig after reading.
- Neither.

If "both" is selected, open the browser first, then invoke the dig skill.

If the deferred option is selected: open the browser per Plan Review Presentation, then wait for the user to report they've finished reading — do not call `ExitPlanMode` yet; ending the turn on plain text would misfire the Stop hook's completion notification. Once they confirm, ask a second `AskUserQuestion` (dig now vs. proceed to approval). dig reads the plan file fresh from disk regardless of when it runs (it's a forked subagent), so deferring costs nothing functionally.

dig rewrites the plan file, so re-present the updated plan afterward, re-applying these rules. If dig runs as a forked/background subagent (it then has no `AskUserQuestion`), treat its returned output as analysis and conduct the confirmation rounds yourself in the main session via `AskUserQuestion`. In plan mode this dialog (or, for the deferred path, the second-round dialog) precedes `ExitPlanMode`. Stop any ephemeral mdts server you started once the review/approval flow completes — never the persistent port-8600 server.

# Fable Model Check Before ExitPlanMode

Immediately before calling `ExitPlanMode`, determine the current session's active model by extracting the session ID from the scratchpad path present in every system prompt (`/private/tmp/claude-<uid>/<project-slug>/<session-id>/scratchpad`) and running:

```bash
jq -r 'select(.type=="assistant" and (.isSidechain//false)==false) | .message.model' \
  ~/.claude/projects/<project-slug>/<session-id>.jsonl | tail -1
```

If the command fails or the result is anything other than `claude-fable-5`, proceed straight to `ExitPlanMode` — do not block on a detection failure.

If the result is `claude-fable-5`, ask a separate `AskUserQuestion` (independent of the Plan Review Deep-Dive dialog — merging them would exceed the 4-option limit) with these three options before calling `ExitPlanMode`:

- Implement with Fable as-is.
- Switch models manually (tell the user to run `/model opus` or similar, then wait for them before resuming implementation).
- Delegate implementation to the Agent tool with `model: "opus"`, passing the full plan content in the prompt.

Proceed to `ExitPlanMode` once the user picks "as-is" or "delegate"; for manual switch, wait for the user to confirm the switch before resuming.

# Settings Changes

Before editing `settings.json` / `settings.local.json` — or its `hooks`, `permissions`, or `env` — in the repository source or the live `~/.claude/` files, invoke the `update-config` skill. Skip it only for trivial mechanical edits (e.g. a verbatim revert) where no configuration-domain judgment is needed.
