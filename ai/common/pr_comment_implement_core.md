Resolve `WORKFLOW_REFERENCE_DIR` from the platform adapter before taking any
workflow action. Confirm these files are readable:

- `analysis-design.md`
- `implementation.md`
- `finalization.md`

If resolution or any required file fails, report the exact path and stop before
creating a worktree, reacting, editing, committing, pushing, replying, or
resolving a thread.

Read `analysis-design.md` first and follow it through Phase 2. Plan mode permits
its read-only analysis, but never its worktree creation or other mutations.
Phase 2 is the only design-approval gate.

After approval, if plan mode deferred mutations, return to
`analysis-design.md`, perform only the deferred 🚀 reaction and worktree
creation with the recorded values, then read `implementation.md` and complete
Phases 3–4. Otherwise begin with `implementation.md`. Then read
`finalization.md` and complete Phase 5 onward. For an accepted no-code-change
result, skip edits and empty commits but still read the finalization workflow
for verification and reply handling. When analysis or the user aborts after a
reaction or worktree exists, read only the finalization reference's abort and
reaction-verification sections.

Carry forward every value recorded by the references, including comment and
thread identifiers, repository and branch identity, worktree path, disposition,
reaction IDs, reply target and location, author role, approval result, changed
paths, and verification results. Never infer an unknown authorization or final
action from the current phase. Stop before the affected external action when
required state is missing.
