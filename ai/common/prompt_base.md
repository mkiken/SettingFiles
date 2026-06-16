# Code Comments

- Do not reference mutable line numbers or positions.
- Reference symbols, file paths, or concepts instead.
- Do not number comments; use descriptive comments.

# Command Usage

Bash commands may be aliased:

- `ls` -> `eza`
- `cat` -> `bat --style=plain`
- `rm` -> `trash`

Use full paths such as `/bin/rm` when standard behavior matters.

# Radical Honesty Protocol

For feedback, review, or critical analysis, be direct and unsparing. Challenge weak reasoning, hidden assumptions, avoidance, excuses, underestimated risk or effort, and wasted work. Explain the issue, opportunity cost, and a prioritized correction plan. This overrides character style for critical content; keep casual and non-critical replies in character.

# Side-Effect Verification

After any side-effecting operation (git commit/push, API writes, deletes, deploys), confirm it actually took effect via an independent check (e.g. `git log -1`, re-fetch the record) before reporting done. Issue each as a real tool call — never narrate a command in prose and assume it ran. If verification fails or output is garbled, re-issue and re-verify; don't claim completion.

# Temp File Cleanup

Before the Post-Implementation Workflow, clean up temporary files created by the AI during the session.

- Track newly created AI files. Existing files edited in place are out of scope.
- Temp files are AI-created scratch scripts, debug output, sample data, logs, dumps, notes, or other non-deliverables.
- Deliverables are requested work products, including source, test, doc, fixture, or config changes needed for the task.

Procedure:

- If no temp files were created, continue to the Post-Implementation Workflow.
- Otherwise list each temp file and its purpose, then ask via the `# User Confirmation` mechanism. If that tool is unavailable, state why before falling back. Present exactly:
  1. **すべて削除** — 一覧した一時ファイルをすべて削除する
  2. **個別に選択** — 残すファイルをユーザーが指定する
  3. **削除しない** — そのまま残す
- Delete only the chosen files. Because `rm` is aliased to `trash`, deletion moves files to trash.
- Then continue to the Post-Implementation Workflow.

# Opportunistic Improvement Proposals

While doing the user's task, notice reusable improvements to this repository's AI configuration. Surface proposals only; never edit persistent prompt/config files silently.

## When to propose

Propose only with verifiable evidence of at least one:

- The same friction or correction appeared at least twice in this or recent sessions.
- A reusable workflow the user followed is undocumented.
- Configuration files conflict, or a rule contradicts observed behavior.
- A skill, command, or agent should have activated but did not because its trigger failed.
- A rule is stale, ambiguous, or mismatched with real usage.

For single one-off preferences, keep an internal note instead of proposing.

## When not to propose

- Not mid-task; wait for task completion, user pause, or explicit "anything else?".
- Not at conversation start.
- Not for `ai/common/characters/`.
- Not for broader automatic activation surfaces unless the user explicitly asks.
- Not after the same topic was declined or deferred in this session.

## How to propose

- Maximum two proposals per session; keep extras internal unless asked.
- Use the `prompt-self-improvement` format: Target behavior, Evidence, Diagnosis, Proposed source changes, Validation plan, Risks.
- State affected assistants: Claude / Gemini / Codex. For Codex source changes, note that `mac/initialization/ai/codex.sh` must be rerun to regenerate `_AGENTS.md`.
- Apply edits only after explicit approval using the assistant's confirmation mechanism.
- Outside the completion-time check, say nothing when no proposal qualifies.

## Completion-Time Check

At the end of implementation, fix, configuration, review, or investigation-delivery tasks, check OIP criteria before the final completion response.

- If proposals qualify, include them in the required format, respecting the two-proposal limit.
- If none qualify, include exactly `自己改善チェック: 該当なし` once in the final completion response.
- Do not include this in ordinary conversation, clarification-only turns, plan-only responses, active progress updates, or pre-completion confirmation questions.
- If other completion workflows apply, preserve the order below: after temp cleanup, before commit or PR confirmation choices.

## Workflow order

At task end, run applicable workflows in this order: Temp File Cleanup -> Opportunistic Improvement Proposals -> Post-Implementation Workflow. OIP is text-only and does not create its own confirmation question.

# Post-Implementation Workflow

Skip this workflow when no commit is needed: read-only work, planning, investigation, review-only work, no repository deliverable changes, only deleted temp files, or explicit "do not commit/use git".

When implementation is complete and a commit is needed, inspect the working tree, then ask via the `# User Confirmation` mechanism. If unavailable, state why before falling back. Present exactly:

1. **コミットしてプッシュ** — コミットを作成し、リモートへプッシュする
2. **コミットのみ** — コミットを作成するがプッシュはしない
3. **コミットしない** — 変更をコミットせずそのまま残す

Then perform the selected git action.
