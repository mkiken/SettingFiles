---
name: plan-model-handoff
description: Detect whether the active Codex model is Sol and confirm the implementation model before finalizing a plan or implementing an accepted plan that lacks a recorded choice. Use only at the handoff checkpoints named by Codex's always-on prompt.
---

# Plan Model Handoff

Run at either checkpoint:

- Immediately before emitting the final `<proposed_plan>` in Plan Mode.
- Immediately before the first implementation side effect for an accepted plan.

## Honor a recorded choice

Treat an accepted plan line matching `Implementation model: parent/<model-id>` or `Implementation model: worker/<model-id>` as authoritative. Do not detect or ask again when a valid marker exists.

For a `parent/` marker, continue in the parent session. For a `worker/` marker, use exactly one `worker` subagent with that model override; assign it all implementation files, tell it other work may coexist in the repository, and retain decisions, integration, and verification in the parent. If the recorded worker model is unavailable in the callable runtime, make no implementation change and run the choice flow again using the currently available overrides.

## Detect the active model

Run this through the host shell, not context-mode:

```zsh
codex_session_file=""
codex_active_model=""
if [[ -n ${CODEX_THREAD_ID:-} ]]; then
  codex_session_file=$(find "$HOME/.codex/sessions" -type f -name "*-${CODEX_THREAD_ID}.jsonl" -print -quit 2>/dev/null)
fi
if [[ -n $codex_session_file ]]; then
  codex_active_model=$(
    jq -r 'select(.type == "turn_context" or .type == "world_state") |
      .payload.model // .payload.state.model // empty' "$codex_session_file" 2>/dev/null |
      tail -1
  )
fi
print -r -- "$codex_active_model"
```

If the result is empty, report `Implementation-model check skipped: active model detection failed.` and continue without asking. If the result does not match `*-sol`, continue silently without asking.

## Choose the implementation model

When the detected model matches `*-sol`, use `request_user_input` when available, otherwise the always-on confirmation fallback, with these choices in this order:

1. `Continue with Sol (Recommended)` — keep implementation in the parent session.
2. `Use Terra subagent` — the parent session remains on Sol; exactly one Terra `worker` subagent performs implementation; the parent retains decisions, integration, and verification.
3. `Use Luna subagent` — the parent session remains on Sol; exactly one Luna `worker` subagent performs implementation; the parent retains decisions, integration, and verification.

Resolve Terra and Luna only from callable runtime metadata, never local configuration. If the selected tier is unavailable, make no implementation change, report the unavailable tier, and offer the choice again.

At the Plan Mode checkpoint, record the result inside the final plan's Assumptions section as exactly one marker:

- `Implementation model: parent/<detected-sol-model-id>`
- `Implementation model: worker/<selected-runtime-model-id>`

At the implementation checkpoint for a plan without a marker, apply the selected execution route to the current task without rewriting the accepted plan.
