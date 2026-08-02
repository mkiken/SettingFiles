---
name: worktree-task
description: Run an implementation task in an isolated Git worktree, then control commit, merge, cleanup, and optional push with explicit checkpoints. Use when the user invokes `$worktree-task` with a task prompt or asks to complete work through the repository's managed worktree workflow.
---

# Worktree Task

Invoke as `$worktree-task <task prompt>`. Treat the text after `$worktree-task` as the task prompt. If it is empty, ask for the task before changing the repository.

Keep the task isolated from the invoking worktree. Defer any ambient post-implementation commit/push workflow until this workflow finishes; do not show its usual three-option confirmation during the isolated task.

## Preserve the workflow through plan mode

When invoked while the active conversation is in plan mode, plan only. Do not
record repository state, invoke `wtc`, create a branch or worktree, or edit
files.

Add this section to the platform's plan artifact:

```markdown
## Worktree Task Handoff

- Implementation entry: `$worktree-task <self-contained task prompt>`
- Scope: Treat the approved plan as the implementation scope and acceptance criteria.
- Start: Before any repository mutation, load the current `worktree-task` instructions and begin at `Record the original state`.
```

Replace the placeholder with a concise prompt that identifies the deliverable
without relying on planning context outside the approved artifact. Keep the
workflow itself in this skill rather than copying it into the plan.

Always include the explicit invocation even when implementation may continue
in the same context. Reloading the instructions is acceptable; execute the
stateful workflow exactly once, only after plan approval. After a context
reset, treat the handoff as a fresh explicit invocation and follow this skill
from `Record the original state` through its remaining checkpoints.

## Record the original state

Before creating a branch or changing files:

1. Resolve and record the invoking worktree's top-level path.
2. Record its current branch and exact `HEAD` object ID.
3. Require the branch to be attached. Stop if `HEAD` is detached.
4. Require `git status --porcelain` to be empty, including untracked files. Stop if dirty.
5. Confirm `wtc` and `wtm` are available in the configured interactive Zsh from the original worktree:

   ```bash
   zsh -ic 'builtin cd -q -- "$1" && type wtc >/dev/null && type wtm >/dev/null' zsh "$original_path"
   ```

   Stop with a clear setup error if either function is unavailable.

Do not stash, clean, reset, or otherwise alter the invoking worktree to bypass these checks.

Use this executable boundary for every configured Zsh function: keep the `-c` script literal, pass paths and branches only as positional arguments, and select the worktree with `builtin cd -q -- "$1"`. Never interpolate task-derived values into the script string.

## Create the task worktree

1. Load `herdr-tab-label` and derive the slug from the task prompt using its shared rules. Retain that slug for both the branch name and the later tab-label attempt.
2. Form `task/<slug>-<timestamp>`. If that local branch exists, append `-2`, `-3`, and so on until the name is unused. Record that the final `refs/heads/<task-branch>` is absent before invoking `wtc`.
3. Run the following from the invoking worktree. It executes exactly `wtc <task-branch> --base <original-branch> --no-cd` semantics through the configured interactive Zsh:

   ```bash
   zsh -ic 'builtin cd -q -- "$1" && wtc "$2" --base "$3" --no-cd' zsh "$original_path" "$task_branch" "$original_branch"
   ```

   Capture its exit status. If it is nonzero, use the failure handling below; never assume a failed `wtc` created nothing.

4. Do not infer the new path from command output or naming conventions. Re-read `git worktree list --porcelain`, match the unique `branch refs/heads/<task-branch>` entry, and record its `worktree` path. If the match is missing or not unique, use the failure handling below.
5. Confirm the task worktree is on the task branch at the recorded original `HEAD`. On failure, use the same failure handling.
6. After validation succeeds, apply `herdr-tab-label` from the invoking path with the existing slug. Use the slug alone—not the `task/` namespace or timestamp. The shared procedure is fail-safe and preserves any non-default tab label; continue the implementation after a reported warning.
7. When `HERDR_ENV=1`, record the validated task worktree for the invoking tab. Herdr popups use this context to open lazygit in the task worktree while the AI pane remains in the invoking worktree. Keep the script literal and values positional; report a warning and continue if recording fails:

   ```bash
   herdr_context_helper="${SET:-$HOME/Desktop/repository/SettingFiles}/shell/tmux/herdr_worktree_context.sh"
   zsh -ic 'builtin cd -q -- "$1" && source "$2" && set_herdr_task_worktree_context "$3"' zsh "$original_path" "$herdr_context_helper" "$task_path"
   ```

### Clear Herdr task-worktree context

After confirming that the task worktree entry is absent, clear its invoking-tab context. Keep the script literal and values positional; report a warning if clearing fails:

```bash
herdr_context_helper="${SET:-$HOME/Desktop/repository/SettingFiles}/shell/tmux/herdr_worktree_context.sh"
zsh -ic 'builtin cd -q -- "$1" && source "$2" && clear_herdr_task_worktree_context' zsh "$original_path" "$herdr_context_helper"
```

### Handle any post-invocation failure

For any failure after the `wtc` invocation—including a nonzero `wtc` exit or subsequent path uniqueness, branch, or `HEAD` validation failure—assume it may have partially created a branch or worktree. Stop before performing the task and gather read-only Git evidence. Do not guess which path or ref belongs to this invocation.

Clean up only if all of these facts are proven:

- The pre-creation check showed `refs/heads/<task-branch>` absent, so this invocation owns the new branch.
- Exactly one worktree entry now identifies that exact task branch and path, and no other worktree uses either one.
- The task branch ref and candidate worktree `HEAD` both equal the recorded original `HEAD`.
- The candidate worktree has empty `git status --porcelain` output and no merge, rebase, or other operation in progress.

When every condition holds, remove that worktree from the recorded invoking worktree, safely delete the task branch, and verify both are absent. If any condition is false or cannot be proven, preserve all state. Never delete ambiguous or changed state. Report the exact candidate worktree paths, refs and object IDs, observed branch and status, and each failed invariant.

## Perform the task

Work only inside the recorded task worktree. Apply the request, run proportionate verification, and remove only temporary artifacts created during this run. Preserve unrelated changes and obey the repository's instructions.

Do not commit or push during implementation. Do not modify the invoking worktree.

## Handle an empty result

If the task worktree remains clean and its `HEAD` still equals the recorded original `HEAD`, skip all commit and push confirmations:

1. From the recorded invoking worktree, remove the task worktree with `git worktree remove <task-worktree>`.
2. Delete the task branch with `git branch -d <task-branch>`.
3. Independently verify that the worktree entry and local branch no longer exist. After the worktree entry is absent, run `Clear Herdr task-worktree context`.
4. Report that the task produced no changes.

Use only safe deletion. If either cleanup operation fails, preserve the remaining state and report it.

## Confirm and create the commit

When deliverable changes exist, summarize the changed paths and verification results. Ask exactly these two authored choices through the platform's user-confirmation mechanism:

- `コミットのみ` — create the task commit and continue to merge; do not push yet
- `コミットしない` — leave the task worktree, branch, and changes intact; do not merge

Do not offer a push choice at this checkpoint. If the user declines the commit, report the preserved worktree path and branch, then stop.

For the commit choice:

1. Recheck the task worktree and stage only paths changed for this task, using explicit paths rather than `git add .` or `git add -A`.
2. Verify the staged diff contains only intended hunks and follow the repository's commit-message convention.
3. Commit in the task worktree. If the commit fails, preserve the worktree and branch, report the failure, and stop.
4. Record the task commit object ID and confirm the task worktree is clean.

## Merge and verify cleanup

Run from the task worktree through the same configured interactive Zsh boundary. This executes exactly `wtm <original-branch>` semantics:

```bash
zsh -ic 'builtin cd -q -- "$1" && wtm "$2"' zsh "$task_path" "$original_branch"
```

Allow normal `git merge` semantics: fast-forward when possible, otherwise a merge commit. Never squash or rebase.

After success, verify merge and cleanup independently:

- Merge: re-read the invoking worktree's branch and `HEAD`, require the recorded task commit to be an ancestor of the original branch, and confirm the invoking worktree is clean.
- Cleanup: require the task worktree entry to be absent and `refs/heads/<task-branch>` not to exist. After the worktree entry is absent, run `Clear Herdr task-worktree context`.

If merge succeeded but cleanup did not, do not push. Report the remaining worktree or branch and the failed check.

## Handle other `wtm` failures

If `wtm` returns nonzero, first inspect
`git diff --name-only --diff-filter=U` and `git ls-files -u` in the invoking
worktree. Use the conflict workflow below only when they identify unmerged
paths.

When no conflicts exist, check whether the recorded task commit is already an
ancestor of the original branch. If it is, do not retry the merge; run the
independent merge and cleanup checks above and report any cleanup failure.

If the task commit is not merged, preserve the invoking worktree, task
worktree, and task branch. Record the exact `wtm` failure output, then inspect
both worktrees' branches, `HEAD` values, `git status --porcelain` output,
operation state, and `git worktree list --porcelain`. Report the blocking
state and the preserved task path, branch, and commit.

Never stash, reset, clean, commit, or otherwise alter unrelated invoking
worktree changes to make `wtm` pass. Do not retry automatically. Retry the
same `wtm <original-branch>` invocation only after the blocker is confirmed
resolved and the invoking worktree is revalidated as clean, attached to the
recorded original branch, and safe to merge.

## Handle merge conflicts

If `wtm` returns nonzero because of conflicts, expect the merge state in the invoking worktree and the task worktree and branch to remain intact.

1. Inspect the invoking worktree with `git diff --name-only --diff-filter=U`, `git ls-files -u`, and focused conflict diffs.
2. Report every conflicted path, explain the competing changes, and give a concrete resolution proposal.
3. Ask exactly these two authored choices through the platform's user-confirmation mechanism:
   - `提案を適用` — resolve the conflicts in the invoking worktree as proposed and continue the merge
   - `自分で解決` — preserve the merge state, task worktree, and task branch for manual resolution, then stop

For agent-applied resolution, edit only the invoking worktree, stage each resolved path explicitly, confirm no unmerged entries remain, and continue the existing merge without rebasing. If the merge continuation fails, preserve all remaining state and stop.

Because the failed `wtm` invocation cannot perform its success cleanup, after confirming the continued merge contains the task commit:

1. From the recorded invoking worktree, remove the task worktree with `git worktree remove <task-worktree>`.
2. After confirming the task worktree entry is absent, run `Clear Herdr task-worktree context`.
3. Delete the task branch with `git branch -d <task-branch>`.
4. Run the same independent merge and cleanup checks required after a conflict-free `wtm` run.

Never abort the merge unless the user explicitly requests it.

## Confirm and perform the push

Only after both merge and cleanup checks pass, ask exactly these two authored choices through the platform's user-confirmation mechanism:

- `プッシュする` — push the updated original branch
- `プッシュしない` — leave the merged original branch local

If the user declines the push, report the local branch and merged commit, then stop.

If the user accepts the push:

1. Re-read the current branch from the recorded invoking worktree. Require it to be attached and equal to the recorded original branch.
2. Resolve its configured upstream remote and remote branch. Stop rather than guessing if no upstream is configured.
3. Fetch that remote and compare the fetched remote ref with the local branch.
4. If the remote is ahead or the histories diverged, stop and report the ahead/behind counts. Never automatically pull, rebase, merge, or force-push.
5. Immediately before pushing, re-read the invoking worktree's current branch again and require the same original branch.
6. Push the current `HEAD` to the configured remote branch without force.
7. Independently query or fetch the remote ref after the push and require its object ID to equal the pushed local commit before reporting success.

If the remote was already equal to the local branch, report that no push was necessary and still verify the remote object ID.
