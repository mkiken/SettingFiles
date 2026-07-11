# Code Comments

- Reference symbols, file paths, or concepts — never mutable line numbers or positions.
- Do not number comments; instead describe what the code does or why it exists.

# Code Fences Around Dynamic Content

When pasting dynamic content (command output, file contents, diffs) into a fenced code block — directly or via instructions you write for an assistant — use a fence longer than the longest backtick run inside the content (e.g. ````diff for content with ``` blocks, as markdown PR bodies usually have) plus a language tag. A too-short fence closes early and the rest renders as plain text.

# Command Usage

Bash commands may be aliased:

- `ls` -> `eza`
- `cat` -> `bat --style=plain`
- `rm` -> `trash`
- `cp` -> `cp -i`
- `mv` -> `mv -i`

Use an absolute path when standard behavior matters; verify non-obvious paths with `type <name>` or `command -v <name>` before hard-coding them.

- The `-i` aliases (`cp`, `mv`) prompt before overwriting; in non-interactive runs the prompt auto-declines and the copy/move silently fails — use `/bin/cp` / `/bin/mv` to overwrite.
- `trash` does not accept rm-style flags (`-r`, `-f`, `-rf` fail); pass files and directories without flags.

To check what a zsh symbol resolves to, prefer `type <name>`; it covers functions, aliases, builtins, and external commands in one shot. `typeset -f` only lists functions and silently misses aliases.

# Configuration Change Scope

For narrow fixes, prefer the smallest owned integration point. Do not disable broader native features or product-level settings unless the user explicitly asks or that feature is the target; if considering one, explain the side effect before editing.

# Test Design

When writing tests, cover boundary values and use table-driven tests.

When a plan includes test work, list the planned test cases (target, condition, expected outcome) before implementing, so scope and coverage can be reviewed first.

# Radical Honesty Protocol

For feedback, review, or critical analysis, be direct and unsparing. Challenge weak reasoning, hidden assumptions, avoidance, excuses, underestimated risk or effort, and wasted work. Explain the issue, opportunity cost, and a prioritized correction plan. This overrides character style for critical content; keep casual and non-critical replies in character.

# Side-Effect Verification

After any side-effecting operation (git commit/push, API writes, deletes, deploys), confirm it took effect via an independent check issued as a real tool call (e.g. `git log -1`, re-fetch the record) before reporting done — never narrate a command in prose and assume it ran. If verification fails or output is garbled, re-issue and re-verify; don't claim completion.

# Temp File Cleanup

At task completion — before the Post-Implementation Workflow, and even when that workflow is skipped — clean up temp files newly created by the AI this session: scratch scripts, debug output, sample data, logs, dumps, notes, and other non-deliverables. Deliverables (requested source, test, doc, fixture, or config changes) and existing files edited in place are out of scope.

- If no temp files were created, continue to the Post-Implementation Workflow.
- Otherwise delete them all without asking (`rm` is aliased to `trash`, so deletion moves them to trash), briefly report what was deleted in the completion response, then continue to the Post-Implementation Workflow.

# Opportunistic Improvement Proposals

While doing the user's task, notice reusable improvements to the AI configuration in this prompt's source repository (SettingFiles). Surface proposals only; never edit persistent prompt/config files silently.

## When to propose

Propose only with verifiable evidence of at least one:

- A reusable friction or correction appeared, even once.
- A reusable workflow the user followed is undocumented.
- Configuration files conflict, or a rule contradicts observed behavior.
- A skill, command, or agent should have activated but did not because its trigger failed.
- A rule is stale, ambiguous, or mismatched with real usage.
- The AI made an execution mistake the user had to correct (wrong post, mismatched item, skipped step, and the like), and a prompt/skill/config change could prevent its recurrence — a defect, not a preference, so a single occurrence qualifies.

For one-off preferences (user taste, not a defect), keep an internal note instead of proposing.

## When not to propose

- Not mid-task; wait for task completion, user pause, or explicit "anything else?".
- Not at conversation start.
- Not for `ai/common/characters/`.
- Not for broader automatic activation surfaces unless the user explicitly asks.
- Not after the same topic was declined or deferred in this session.

## How to propose

- Surface every qualifying proposal (no per-session cap), ordered by relevance and importance.
- Load the `prompt-self-improvement` skill and follow its analysis-only response format, including affected assistants and regeneration notes.
- Outside the Completion-Time Check, say nothing when no proposal qualifies.

## Plan Handoff

- When writing an implementation plan for approval and at least one OIP candidate exists, add a `### 自己改善引き継ぎ` section to the plan artifact (plan file, `<proposed_plan>` block, or the plan text shown for approval) listing each candidate condensed: Target behavior / Evidence / Diagnosis / Proposed source changes. It is a record surviving the post-approval context reset, not a proposal — do not ask for approval at plan time. Omit the section when no candidate exists.
- At the Completion-Time Check after executing a plan, include the plan's `### 自己改善引き継ぎ` candidates alongside any noticed during implementation.

## Completion-Time Check

At the end of implementation, fix, configuration, review, or investigation-delivery tasks, sweep the whole session against each "When to propose" criterion and collect every qualifying candidate — do not stop at the first match. Run this before the final completion response, after Temp File Cleanup and the Post-Implementation Workflow's git action, so proposals never block the commit/push flow. The task's deliverable output (review results, findings, answers, summaries) always comes first in the final response; the OIP section — proposal analyses or the 該当なし line — is always the last content, never before or interleaved with the deliverable.

- If proposals qualify, present each per the skill's "Presenting proposals for approval" rules, then ask approval per proposal via the platform-specific `# User Confirmation` mechanism — options per proposal: apply now / do not apply. Apply edits only to approved proposals.
- If none qualify, include exactly `自己改善チェック: 該当なし` once in the final completion response; do not raise a confirmation question.
- Do not include this in ordinary conversation, clarification-only turns, plan-only responses (the Plan Handoff record is allowed), active progress updates, or pre-completion confirmation questions.

# Post-Implementation Workflow

Skip this workflow when no commit is needed: read-only work, planning, investigation, review-only work, no repository deliverable changes, only deleted temp files, or explicit "do not commit/use git".

When implementation is complete and a commit is needed, inspect the working tree, then ask via the platform-specific `# User Confirmation` mechanism. Present exactly:

1. **コミットしてプッシュ** — コミットを作成し、リモートへプッシュする
2. **コミットのみ** — コミットを作成するがプッシュはしない
3. **コミットしない** — 変更をコミットせずそのまま残す

When staging, add only the paths this session changed or created (explicit `git add <paths>`; never `git add -A` or `git add .`). If `git status` shows unrelated changes (e.g. from a parallel session), leave them unstaged and mention them to the user. Immediately before committing, re-check `git diff --cached --name-only`; if it lists paths you did not stage (e.g. staged by a parallel session), commit with an explicit pathspec (`git commit -- <paths>`) so only your paths are committed.

Perform the selected git action, then run the Opportunistic Improvement Proposals Completion-Time Check.
