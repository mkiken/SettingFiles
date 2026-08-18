---
name: plan-model-handoff
description: Detect whether the active Codex model is Sol and confirm how to implement an accepted plan. Use only immediately before the first implementation side effect.
---

# Plan Model Handoff

Run only immediately before the first implementation side effect for an accepted plan.

Do not write an implementation-model marker into a newly finalized plan. The user must be able to inspect the completed `<proposed_plan>` before choosing how implementation runs.

## Honor a legacy recorded choice

For backward compatibility, treat an accepted older plan line matching `Implementation model: parent/<model-id>` or `Implementation model: worker/<model-id>` as authoritative. Do not detect or ask again when a valid legacy marker exists.

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

## Choose the implementation route

When the detected model matches `*-sol`, use `request_user_input` when available, otherwise the always-on confirmation fallback, with these choices in this order:

1. `Continue with Sol (Recommended)` — keep implementation in the parent session.
2. `Use Terra subagent` — the parent session remains on Sol; exactly one Terra `worker` subagent performs implementation; the parent retains decisions, integration, and verification.
3. `Use Luna subagent` — the parent session remains on Sol; exactly one Luna `worker` subagent performs implementation; the parent retains decisions, integration, and verification.

Resolve Terra and Luna only from callable runtime metadata, never local configuration. If the selected tier is unavailable, make no implementation change, report the unavailable tier, and offer the choice again.

Free-form `Other` means a manual parent-session model switch, not Terra/Luna worker delegation. Make no implementation change. Ask the user to switch the parent session model manually, wait until the user confirms the switch, then rerun detection on the next implementation attempt.

For an accepted plan without a valid legacy marker, apply the selected execution route to the current task without rewriting the accepted plan.
