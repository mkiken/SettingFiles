---
name: plan-model-handoff
description: Detect whether the active Codex model is Sol and choose how to execute an accepted plan. Use only when beginning accepted-plan execution, before any task-specific workflow or repository operation.
---

# Plan Model Handoff

Run only when beginning execution of an accepted plan, before starting any
task-specific workflow or repository operation for that plan.

Do not write an implementation-model marker into a newly finalized plan. The user must be able to inspect the completed `<proposed_plan>` before choosing how implementation runs.

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

1. `Continue with Sol (Recommended)` — keep the entire accepted-plan execution in the parent session.
2. `Use Terra subagent` — the parent session remains on Sol; exactly one Terra `worker` subagent owns the entire accepted-plan execution.
3. `Use Luna subagent` — the parent session remains on Sol; exactly one Luna `worker` subagent owns the entire accepted-plan execution.

Resolve Terra and Luna only from callable runtime metadata, never local configuration. If the selected tier is unavailable, make no implementation change, report the unavailable tier, and offer the choice again.

Free-form `Other` means a manual parent-session model switch, not Terra/Luna worker delegation. Make no implementation change. Ask the user to switch the parent session model manually, wait until the user confirms the switch, then rerun detection on the next implementation attempt.

Apply the selected execution route to the current task without rewriting the accepted plan.

## Delegate the full execution lifecycle

For Terra or Luna, spawn exactly one `worker` with the selected runtime model
override and `fork_turns="none"`. Give it a self-contained prompt containing:

- The accepted plan verbatim, the original task request, and every accepted user decision.
- Every implementation handoff from the plan, including an explicit `$worktree-task ...` entry when present.
- Instructions to load current applicable skills before acting and to treat the plan as its complete scope and acceptance criteria.
- Notice that other work may coexist in the repository and it must preserve changes it does not own.

Assign the worker the whole task lifecycle: task-workflow setup and state
capture, implementation, verification, user confirmations, commits, merges,
pushes, in-scope PR or issue replies and resolution, cleanup, independent
side-effect verification, and the final report. The worker must follow every
applicable workflow and confirmation boundary; delegation grants no new
authority.

The worker should surface required user confirmations itself. If its thread
cannot surface a confirmation, it must send the exact question and authored
choices to the parent. The parent relays them unchanged, sends the user's
answer back to the worker, and makes no decision on the worker's behalf.

While the worker runs, the parent may wait, forward new user instructions, and
relay confirmations or results. It must not independently inspect or change
the repository, run verification, integrate changes, commit, push, post or
resolve PR or issue content, or take over any unfinished task work.

If the worker fails, stops, or reports a blocker, the parent relays its failure
and preserved-state report, then stops. It must not retry, spawn a replacement,
or continue with Sol unless the user gives a new explicit instruction.
