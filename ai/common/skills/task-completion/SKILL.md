---
name: task-completion
description: End-of-task procedure — temp file cleanup, commit/push confirmation, and the improvement-proposal check.
---

# Task Completion

Run in this order when finishing a task: Temp File Cleanup, then the Post-Implementation Workflow, then the Opportunistic Improvement Proposals Completion-Time Check.

## Temp File Cleanup

At task completion, before the Post-Implementation Workflow even when skipped, clean up this session's AI-created non-deliverable temp files (scratch scripts, debug output, sample data, logs, dumps, notes). Exclude requested source, tests, docs, fixtures, or config changes and existing files edited in place.

- Establish provenance before deleting a temp-looking file: use a pre-task baseline or direct evidence that this session created it. Never infer ownership from its name, contents, or timestamps alone; if provenance is uncertain, leave it in place and report it.
- Before calling `trash`, resolve and validate each target as a non-empty, existing, explicit path; never pass unset or empty variables or rely on the current working directory. If validation fails, leave the target untouched and report it.
- Delete them all without asking — invoke `trash` directly — and briefly report what was deleted in the completion response. Whether or not any temp files existed, then continue to the Post-Implementation Workflow.

## Post-Implementation Workflow

Skip this workflow when no commit is needed: read-only work, planning, investigation, review-only work, no repository deliverable changes, only deleted temp files, or explicit "do not commit/use git".

When implementation is complete and a commit is needed, inspect the working tree, then ask whether to commit and push, commit only, or leave changes uncommitted via the platform-specific `# User Confirmation` mechanism. Before asking, display the current branch, push remote, and destination branch; mark any unresolved value as unknown instead of guessing. Resolve the destination from the planned push: do not infer the destination branch from the upstream when the planned push uses the current branch name. For Claude and Gemini, present exactly:

1. **コミットしてプッシュ** — コミットを作成し、リモートへプッシュする
2. **コミットのみ** — コミットを作成するがプッシュはしない
3. **コミットしない** — 変更をコミットせずそのまま残す

Stage only the paths this session changed or created — explicit `git add <paths>` with literal paths as a standalone command (no pipelines, `xargs`, or `&&` chains, which bypass permission allow rules), never `git add -A`/`git add .`. Before committing:

- Unrelated changes in `git status` (e.g. a parallel session's): leave unstaged, mention them to the user.
- An unrelated path shown as staged: run `git log -1` first — the same "M" marker covers both staged-but-uncommitted and a parallel session's mid-session commit, and one command settles which.
- Re-check `git diff --cached --name-only`: if it lists paths you did not stage, unstage them (`git restore --staged <paths>` — note this touches a parallel session's staging) and commit with no pathspec; a pathspec-scoped commit captures working-tree content — including another session's unstaged edits and a rebuilt index blob — bypassing the partial index.
- Skim `git diff --cached` hunk by hunk for any file touched elsewhere this session and confirm this session authored every hunk. A path check alone misses this: a parallel session's commit captures the whole working tree, including this session's unsaved edits to that file.

Perform the selected git action, then run the Opportunistic Improvement Proposals Completion-Time Check.

## Opportunistic Improvement Proposals

### When to propose

Propose only with verifiable evidence of at least one:

- A reusable friction appeared, even once: a tool call or command failed or had to be retried because a prompt, skill, or config gave wrong or missing guidance, or the user had to supply information the configuration should have provided.
- A reusable workflow the user followed is undocumented.
- Configuration files conflict, or a rule contradicts observed behavior.
- A skill, command, or agent should have activated but did not because its trigger failed.
- A rule is stale, ambiguous, or mismatched with real usage.
- The AI made an execution mistake the user had to correct (wrong post, mismatched item, skipped step, and the like), and a prompt/skill/config change could prevent its recurrence — a defect, not a preference, so a single occurrence qualifies.

For one-off preferences (user taste, not a defect), keep an internal note instead of proposing.

### When not to propose

- Not mid-task; wait for task completion, user pause, or explicit "anything else?".
- Not at conversation start.
- Not for `ai/common/characters/`.
- Not for broader automatic activation surfaces unless the user explicitly asks.
- Not after the same topic was declined or deferred in this session.
- Not for a single corrective retry in the same turn, with no additional user input, after which the original task resumes and completes. This exclusion does not apply to additional user confirmation or instructions, a second retry, a task that does not resume or is interrupted, a dangerous operation, or the same root cause recurring in the session.

### Completion-Time Check

After implementation, fix, configuration, review, or investigation-delivery tasks, check the whole session against every "When to propose" criterion and collect all qualifying candidates, not only the first. Run this after Temp File Cleanup and the Post-Implementation Workflow git action; place it last in the final response, after deliverables.

- Any candidate qualifies (including a `### 自己改善引き継ぎ` record carried in an executed plan): load the `prompt-self-improvement` skill and follow its "Opportunistic Improvement Proposals" section for presentation, ordering, and per-proposal approval.
- None qualify: include exactly `自己改善チェック: 該当なし` once, do not load the skill, and do not raise a confirmation question.
