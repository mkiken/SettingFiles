# User Confirmation

Do not use the `request_user_input` tool in Codex.

Ask confirmation, clarification, cleanup, commit, and PR workflow questions in plain text as the final response.

Reason: `request_user_input` waits do not emit Codex hook events, so Stop/notification hooks do not run and tmux can remain in the ongoing state.

This rule takes precedence over shared instructions or skill instructions that mention Ask-style tools.
