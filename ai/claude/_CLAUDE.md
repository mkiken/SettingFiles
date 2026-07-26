@../common/prompt_base.md

# Character
@../common/characters/reimu.md

# User Confirmation

When asking for confirmation, clarification, or any question requiring a user response, you MUST use the `AskUserQuestion` tool instead of plain text output. Plain text fallbacks are forbidden except when the tool truly cannot be invoked in the current mode, in which case you must state explicitly why the fallback is needed.

Plain text questions end the turn and trigger the Stop hook, sending a "finished" notification indistinguishable from task completion; `AskUserQuestion` keeps the turn active and triggers the correct "awaiting input" notification.

`AskUserQuestion` supports 2–4 options per question; design confirmation menus within 4 options and route overflow choices (e.g. "do nothing") through the auto-provided free-form "Other".

When a question depends on explanatory context (proposals, trade-offs, anything not self-evident), make it self-contained: put the essential context in the `question` field itself, with options' `description`/`preview` as supplements. Response text that precedes a tool call in the same turn may not be displayed to the user, or may not appear adjacent to the dialog — never leave the explanation only in earlier text.

**Note:** `AskUserQuestion` is a deferred tool in Claude Code — its schema is not loaded by default. If you have not yet loaded its schema this session, call `ToolSearch` with the query `select:AskUserQuestion` first, then invoke `AskUserQuestion`. "I do not have access to the tool" is NOT a valid reason to skip — load the schema and use it.

# Plan Review Deep-Dive (dig)

When presenting a plan artifact for review, also offer the `dig` skill when the plan involves design decisions (new feature, architecture change), still carries assumptions or open items (TBD, 要検討), or spans multiple phases / many tasks. Skip it for mechanically obvious plans (renames, bulk replacements, small fixes).

Merge this with the Plan Review Presentation offer into a single `AskUserQuestion` dialog (single-select, no multiSelect): a browser option when the mdts criteria hold, a dig option when the uncertainty criteria hold, a decline option, and — only when both criteria hold — a fourth option to open the browser and decide on dig after reading, since dig is most useful once the user knows where the plan's gaps are. If dig is selected outright, open the browser first (when also selected), then invoke the dig skill.

If the deferred option is selected: open the browser per Plan Review Presentation, then wait for the user to report they've finished reading — do not call `ExitPlanMode` yet; ending the turn on plain text would misfire the Stop hook's completion notification. Once they confirm, ask a second `AskUserQuestion` (dig now vs. proceed to approval). dig reads the plan file fresh from disk regardless of when it runs (it's a forked subagent), so deferring costs nothing functionally.

dig rewrites the plan file, so re-present the updated plan afterward, re-applying these rules. If dig runs as a forked/background subagent (it then has no `AskUserQuestion`), treat its returned output as analysis and conduct the confirmation rounds yourself in the main session via `AskUserQuestion`. In plan mode this dialog (or, for the deferred path, the second-round dialog) precedes `ExitPlanMode`. Stop any mdts server you started once the review/approval flow completes.

# Settings Changes

Before editing `settings.json` / `settings.local.json` — or its `hooks`, `permissions`, or `env` — in the repository source or the live `~/.claude/` files, invoke the `update-config` skill; its description covers settings edits, permission changes, env vars, and hook troubleshooting. Skip it only for trivial mechanical edits (e.g. a verbatim revert) where no configuration-domain judgment is needed.
