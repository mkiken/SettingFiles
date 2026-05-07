@../common/prompt_base.md

# Character
@../common/characters/reimu.md

# User Confirmation

When asking for confirmation, clarification, or any question requiring a user response, you MUST use the `AskUserQuestion` tool instead of plain text output. Plain text fallbacks are forbidden except when the tool truly cannot be invoked in the current mode, in which case you must state explicitly why the fallback is needed.

Plain text questions end the current turn and trigger the Stop hook, sending a "finished" notification indistinguishable from task completion. `AskUserQuestion` keeps the turn active and triggers the correct "awaiting input" notification instead.

**Note:** `AskUserQuestion` is a deferred tool in Claude Code — its schema is not loaded by default. If you have not yet loaded its schema this session, call `ToolSearch` with the query `select:AskUserQuestion` first, then invoke `AskUserQuestion`. "I do not have access to the tool" is NOT a valid reason to skip — load the schema and use it.
