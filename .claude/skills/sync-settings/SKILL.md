---
name: sync-settings
description: Sync this SettingFiles checkout's committed configuration changes into the current Mac. Use when asked to reflect changes from another PC or sync settings, optionally for specified commits, a revision range, or named settings.
---

# Sync Settings

Project-local skill shared by Claude and Codex. Operate on this SettingFiles checkout, never another repository inferred from the current directory. Resolve the project root and read its instructions and applicable domain skills. In plan mode, inspect and propose only.

## Resolve the request and source

- User instructions take priority: accept natural-language scope, a single commit, a Git revision range, or named settings. Clarify ambiguous revisions or scope before dependent work. Validate revisions as commits before using them; do not interpolate user text into shell code.
- Inspect the branch, upstream, working tree (including untracked files), and any Git operation in progress. Stop on uncommitted changes, an in-progress operation, detached HEAD, or missing upstream. Never stash, reset, clean, or automatically rebase.
- Unless instructed otherwise, fetch the configured upstream and update only by fast-forward. Stop on divergence or fetch/update failure. Independently verify the resulting HEAD and clean working tree. Freeze that commit as the target for this run; stop if the source changes while applying.
- Explicit scope replaces automatic boundary discovery. A single commit selects its changes; a range uses Git's range semantics. An older commit is not permission to roll back newer settings: inspect the target version and ask if the request conflicts with it.

## Discover unapplied changes

Without an explicit commit selection, walk from target HEAD newest to oldest along first-parent history. For a merge, inspect its diff against its first parent so changes brought in by the merge are included.

For each commit, read its actual diff and the relevant setup functions and callers. Identify every applicable environment effect, not just changed filenames. Respect the repository's current environment scope. Documentation/test-only commits and changes with no environment effect are skipped, never used as a stopping boundary.

Compare the effects with the real environment: configuration keys, symlink destinations, regular-file contents, installed components, and reload requirements where observable. A linked source file may already reflect Git's update while a merged config or a newly added link still needs work. A commit is fully applied only when all applicable effects are verified. Partial application and unknown status are not proof of application; continue searching and retain their unresolved items.

Stop at the first fully applied commit and exclude that boundary from the selected changes. This deliberately can miss older unapplied changes on a partially synchronized PC; state that limitation with the discovered boundary. Do not create a per-PC applied-commit marker. If no boundary can be proven, including with shallow or missing history, ask for a starting commit/range before applying anything; do not silently choose a cutoff or replay the entire history.

## Prepare the minimal application

Read all selected changes and consolidate their still-effective actions by setting, respecting dependencies. Use the frozen target version: do not replay superseded values or resurrect removed settings. Keep deletion and migration effects visible even when the old source no longer exists.

Prefer existing narrowly scoped setup helpers after inspecting their side effects. Do not run all of `mac/update`, full initialization, unrelated package upgrades, or a broad AI-tool update just to reflect a few settings. Do not add a persistent path-to-action heuristic or generate new scripts for each run.

Before executing, show selected commits and boundary, already-applied effects, unresolved effects, exact live write destinations (resolve symlink parents), proposed actions, and verification for each. Obtain confirmations required by project instructions for external writes, deletions, installation, or other external effects, grouped into one reviewable decision. Existing authorization still applies; do not ask again for the same approved action.

For copied/merged configurations, change only verified relevant keys and preserve machine-local values. Repository deletions do not automatically propagate through additive merges: propose the specific live removal explicitly. Interactive helpers can silently keep the destination in noninteractive runs; inspect their behavior and verify the live result instead of treating exit zero as application.

## Apply and verify

Execute only approved, in-scope actions. On failure, stop dependent actions and report what succeeded, what failed, and what remains; do not retry blindly or claim full synchronization. Reinspect the environment on the next run rather than trusting an earlier partial execution.

Verify every effect with an independent read: parse the live config and inspect relevant keys, read links and resolve their targets, compare installed regular files, or query the actual component state. Distinguish a file updated on disk from a running process that needs restart/reload; do not claim runtime verification without evidence from that context.

Report the frozen source commit, selected range/boundary, applied and already-applied items, failures, unverified items, and any required restart. Describe synchronization as limited to the checked scope; when using an automatic boundary, explicitly say older changes were not checked and may remain unapplied. If nothing needs changing, report the observed evidence and perform no writes. Do not commit or push repository changes as part of synchronization unless separately requested.
