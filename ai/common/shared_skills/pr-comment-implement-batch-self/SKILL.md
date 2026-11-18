---
name: pr-comment-implement-batch-self
description: Handle all unresolved review threads of the current branch's PR like pr-comment-implement-batch, but auto-fix and commit clear behavior-preserving threads without approval. Use for an explicit self batch PR-comment request.
---

# PR Comment Implement (Batch, Self)

Same workflow as `pr-comment-implement-batch`, with these changes: clear
behavior-preserving threads are fixed and committed without per-thread
approval, and the opening confirmations are reduced.

Resolve this skill directory's real path and read its sibling
`../pr-comment-implement-batch/SKILL.md`, plus `../pr-self-review/SKILL.md`
section "Repair findings". Follow the batch skill's "Establish the target",
"Collect threads", "Analyst brief" and "Finalize" unchanged, and its
"Per-thread loop" for every `approval` thread. Stop if either file cannot be read.

## Changed flow

1. Establish the target and collect threads as the batch skill does.
2. Do not ask for the flow. Use the batch skill's "Choose flow" recommendation
   (Inline when every thread is a small local fix, else Subagents).
3. Analyze every thread first with the Analyst brief and classify it:
   - `auto`: disposition `implement` AND all of pr-self-review's automatic-repair
     conditions hold: proven by explicit repository rules or existing contracts,
     unambiguous and local solution, behavior unchanged, verifiable by targeted
     checks. Confidence or a "bad practice" label alone is insufficient.
   - `approval`: everything else, including every behavior change (even an
     obvious bug fix), uncertain behavior preservation, `reject`,
     `already-satisfied` and `needs-user-decision`.
4. Skip selection: list all threads as the batch skill does, marking `auto`
   ones as "auto-fix planned". `auto` threads are not skip candidates. Ask which
   `approval` threads to skip (none / numbers). Skip the question when there are
   none.
5. Per-thread loop, strictly serial in list order:
   - `auto`: no approval. Implement, pin the change with a test when behavior is
     observable, run the repository's targeted checks and `git diff --check`,
     stage explicit paths only, commit that thread alone following the
     repository convention. Record commit hash, `auto`, reply draft.
   - `approval`: batch skill's loop unchanged.
   - If an `auto` thread fails verification or raises a new design choice, stop
     that thread, report partial edits, demote it to `approval` and ask
     (承認 / 修正依頼 / スキップ). Never commit unverified work.
6. Finalize as the batch skill does (single confirmation for push, reply and
   resolve; never force-push). The final per-thread table also shows whether
   each commit was `auto` or `approved`.
