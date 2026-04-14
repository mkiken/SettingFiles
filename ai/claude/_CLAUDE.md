@../common/prompt_base.md

# Character
@../common/characters/reimu.md

# User Confirmation

When asking for confirmation, clarification, or any question requiring a user response, always use the `AskUserQuestion` tool instead of plain text output.

Plain text questions end the current turn and trigger the Stop hook, sending a "finished" notification indistinguishable from task completion. `AskUserQuestion` keeps the turn active and triggers the correct "awaiting input" notification instead.
