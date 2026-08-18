# Code Comments

- Reference symbols, file paths, or concepts — never mutable line numbers or positions.
- Do not number comments; instead describe what the code does or why it exists.

# File References When Addressing the User

When pointing the user at a file or code location — in questions, confirmation dialogs, or findings — use a repository-root-relative path plus `:line` when known; bare filenames are ambiguous in large repositories and not self-contained. (Line numbers are fine here — unlike code comments, these messages are ephemeral.)

# Code Fences Around Dynamic Content

When pasting dynamic content (command output, file contents, diffs) into a fenced code block — directly or via instructions you write for an assistant — use a fence longer than the longest backtick run inside the content (e.g. ````diff for content with ``` blocks, as markdown PR bodies usually have) plus a language tag. A too-short fence closes early and the rest renders as plain text.

# Dynamic Result Output

Before emitting dynamically selected result rows, count them and branch on the count. At more than 100 lines—or when few lines carry a large payload (minified JSON, base64, long single lines)—do not print the rows in the same call; print only the count and a focused summary, then narrow or paginate in a follow-up.

# Command Usage

Bash commands may be aliased:

- `ls` -> `eza`
- `cat` -> `bat --style=plain`
- `rm` -> `trash`
- `cp` -> `cp -i`
- `mv` -> `mv -i`
- `rg` -> `RIPGREP_CONFIG_PATH=${SET:-$HOME/Desktop/repository/SettingFiles/}configs/.ripgreprc rg`

Use an absolute path when standard behavior matters; verify non-obvious paths with `type <name>` or `command -v <name>` before hard-coding them.

When declaring shell variables, avoid zsh special parameters such as `status` and `path`; use task-specific names such as `test_exit`.

- The `-i` aliases (`cp`, `mv`) prompt before overwriting; in non-interactive runs the prompt auto-declines and the copy/move silently fails — use `/bin/cp` / `/bin/mv` to overwrite.
- Deletion is the exception to that `/bin/` escape hatch: `rm` and `/bin/rm` are permission-denied in all cases, even non-interactively — always delete via `trash`.
- `trash` does not accept rm-style flags (`-r`, `-f`, `-rf` fail); pass files and directories without flags.
- `eza` does not accept GNU/BSD `ls` flags: it hard-errors on flags like `-t` (its `--time <FIELD>` expects a named value) instead of behaving like `ls`. When a flag's meaning must match traditional `ls`, use `/bin/ls`.

To check what a zsh symbol resolves to, prefer `type <name>`; it covers functions, aliases, builtins, and external commands in one shot. `typeset -f` only lists functions and silently misses aliases.

# Context-Mode Commands

For `ctx_batch_execute`, use one `commands` entry per target. Avoid shell control-flow or compound constructs (`if`/`case`/`for`/`while`, parenthesized command groups, and subshells) inside a command string because the runner may not parse them. When the operation requires those constructs, use a host-shell command and keep its output bounded with focused filters, counts, or summaries.

`ctx_batch_execute` requires a non-empty `queries` array; when no follow-up search is needed, pass one query matching what the commands should answer. Before adding more `queries`, bound the search fan-out (query count times returned matches). For large outputs, request only a count or focused summary inline, then use narrower follow-up searches or programmatic extraction; do not let search results bypass the 100-line Dynamic Result Output limit.

If a context-mode tool rejects a read because the target resolves outside the active project root, do not retry the same call. Run a host-shell command from the target repository and keep its output bounded instead of printing the full file or result set.

# Cross-Repository Work

Before working on files in a repository other than the session's project — editing, running its tooling, or committing there — read that repository's root AI instruction file (CLAUDE.md / AGENTS.md / GEMINI.md, whichever exists) and follow it, including commit message conventions and pre-commit verification; out-of-project instruction files are not auto-loaded into the session.

If a workflow or tool resolves a write target outside the session project, display the exact target and obtain confirmation before mutating it, unless the user explicitly named that external target.

# Configuration Change Scope

For narrow fixes, prefer the smallest owned integration point. Do not disable broader native features or product-level settings unless the user explicitly asks or that feature is the target; if considering one, explain the side effect before editing.

# Fail-Safe Defaults

When introducing a flag or parameter that gates a destructive or billable operation (dry-run, force, auto-approve, etc.), propose the fail-safe default (e.g. dry-run enabled, force disabled). If existing codebase convention points the other way, do not silently follow it — surface the default-value choice as an explicit confirmation item.

# Test Design

When a plan includes test work, list the planned test cases (target, condition, expected outcome) before implementing, so scope and coverage can be reviewed first.

When a code comment declares a defensive invariant ("X is never adopted", "Y cannot happen"), add a test pinning that invariant in the same commit — an unenforced comment reads as already-handled and hides the missing guard.

# Diagnostic Check Results

When a relevant diagnostic or check command exits non-zero due to pre-existing findings, distinguish baseline findings from findings introduced by the current task. Report the non-zero result accurately; do not call the command successful solely because no new findings were introduced.

# Performance Work

Before designing a performance optimization, measure the baseline and each candidate's dominant cost (process startup, I/O, etc.) and include the numbers in the plan. Claim a speedup only after re-measuring, never from theory alone.

# Heuristic Design

Before designing a heuristic that classifies or filters inputs (string patterns, allowlists, thresholds), measure the distribution its assumptions rest on against real data — the full population, or a sample with the sampling policy stated — and include the numbers in the plan. Never generalize from a few convenient examples.

# Radical Honesty Protocol

For feedback, review, or critical analysis, be direct and unsparing. Challenge weak reasoning, hidden assumptions, avoidance, excuses, underestimated risk or effort, and wasted work. Explain the issue, opportunity cost, and a prioritized correction plan. This overrides character style for critical content; keep casual and non-critical replies in character.

# Foreign-Context Debugging

When a bug lives in an execution context you cannot run directly (another process's child: popup, hook, cron job), do not treat a reproduction built from your own session's environment as verification — inherited env vars silently differ. Capture the real context's environment and inputs first (instrument the actual trigger; ask the user to fire it once if needed), then diagnose. Until then, report findings as hypotheses, not verified fixes.

# Side-Effect Verification

After any side-effecting operation (git commit/push, API writes, deletes, deploys), confirm it took effect via an independent check issued as a real tool call (e.g. `git log -1`, re-fetch the record) before reporting done — never narrate a command in prose and assume it ran. If verification fails or output is garbled, re-issue and re-verify; don't claim completion.

Report a tool call's outcome only from the text that call actually returned — never compose, reconstruct, or pre-fill its output (a commit hash, changed-file count, a push's ref-update line). If you have not yet seen the result, you do not know it; say so instead of supplying a plausible one.

Before `git push`, never hard-code the target branch — run `git branch --show-current` immediately before push, push that branch, and verify its remote ref advanced afterward. A parallel session may re-point the branch mid-task, and a hard-coded target can silently no-op (`Everything up-to-date`) while the current branch's commits stay unpushed.

# Destructive-Command Verification Safety

When verifying newly written code or shell functions that invoke destructive commands (`git restore`, `git clean`, `rm`, force-overwrite, etc.), never run that verification against a real project repository — set up a disposable throwaway repo/directory (e.g. `mktemp -d` + `git init`) and exercise the code there instead. When mocking a confirmation gate (e.g. a `confirm` function) to test the flow, also mock or stub out the destructive commands gated behind it — mocking only the gate while leaving real destructive commands live is not a safe test.

Before running an external installer in a disposable target, identify and baseline its known shared or global state roots; a temporary destination alone does not prove isolation. Compare those roots afterward and clean up only artifacts attributable to the run.

# Visual Verification

When showing the user something to visually confirm (e.g. a tmux popup), state what to check before opening it, keep it open until the user dismisses it (never close on a timer), and use a dedicated unambiguous fixture as the test subject — not whatever file happens to be newest.

# Plan Review Presentation

When presenting a markdown plan artifact (plan-mode plan file, SDD spec/design/tasks document) for user review or approval, offer to render it in the browser when any of the following holds; otherwise skip the offer:

- It is an SDD spec/design/tasks document (always offer).
- It is 100 lines or longer.
- It contains mermaid diagrams, tables, or images.
- The plan spans multiple files.

Ask via the platform-specific `# User Confirmation` mechanism. If accepted, launch mdts in the background — the launch shape depends on the artifact.

mdts's own `-p auto` scans upward from its default port (8521) and gives up after 10 tries, colliding with the user's own manual `mdts` (which also defaults to 8521) and eventually exhausting the whole default band. Ephemeral AI-launched instances must instead pick a free port starting from 8610, reserving 8521+ for the user's manual use — find one with a shell loop before invoking mdts, e.g.:

```bash
for p in $(seq 8610 8620); do
  if ! /usr/sbin/lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1; then echo "$p"; break; fi
done
```

Passing that number explicitly (not `auto`) is required — `-p <number>` still fails outright on collision (mdts does not retry a numeric port), so the free-port search above must run first every time, even when a prior probe succeeded.

- **Plan-mode plan file** (a single file among many in `~/.claude/plans/`): reuse a persistent server on the fixed port 8600, mounting `~/.claude/plans`. Probe first (e.g. `curl -s -o /dev/null http://localhost:8600/api/filetree`); only start it if the probe fails. **Never stop this server** — a fixed port keeps the browser origin (and therefore its `localStorage`-backed layout/sidebar preferences) stable across reviews, and killing it drops any tab the user still has open on it. Open the target directly via `http://localhost:8600/<filename>` — no glob needed since the file tree stays collapsed by user preference. If port 8600 is already taken by something else, find a free port as above and fall back to `mdts -p <found-port> --no-open ~/.claude/plans -g '<filename>'` for that one review (directory argument before `-g` — it is variadic and will otherwise swallow the directory, silently mounting the wrong path and watching zero files), and treat that instance as ephemeral like the SDD case below.
- **Small self-contained directory** (e.g. an SDD feature directory): find a free port as above and run `mdts -p <found-port> --no-open <that directory>` per review; stop it once the user finishes — never on a timer.

Tell the user which file to review in either case.

# Temp File Cleanup

At task completion — before the Post-Implementation Workflow, and even when that workflow is skipped — clean up temp files newly created by the AI this session: scratch scripts, debug output, sample data, logs, dumps, notes, and other non-deliverables. Deliverables (requested source, test, doc, fixture, or config changes) and existing files edited in place are out of scope.

- Establish provenance before deleting a temp-looking file: use a pre-task baseline or direct evidence that this session created it. Never infer ownership from its name, contents, or timestamps alone; if provenance is uncertain, leave it in place and report it.
- Before calling `trash`, resolve and validate each target as a non-empty, existing, explicit path; never pass unset or empty variables or rely on the current working directory. If validation fails, leave the target untouched and report it.
- If no temp files were created, continue to the Post-Implementation Workflow.
- Otherwise delete them all without asking — invoke `trash` directly, never `rm`/`/bin/rm` (non-interactive shells skip the `rm` -> `trash` alias) — briefly report what was deleted in the completion response, then continue to the Post-Implementation Workflow.

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
- Not for a single corrective retry in the same turn, with no additional user input, after which the original task resumes and completes. This exclusion does not apply to additional user confirmation or instructions, a second retry, a task that does not resume or is interrupted, a dangerous operation, or the same root cause recurring in the session.

## Completion-Time Check

At the end of implementation, fix, configuration, review, or investigation-delivery tasks, sweep the whole session against every "When to propose" criterion and collect all qualifying candidates — do not stop at the first match. Run it after Temp File Cleanup and the Post-Implementation Workflow's git action, and place it last in the final completion response, after the task's deliverable output.

- Any candidate qualifies (including a `### 自己改善引き継ぎ` record carried in an executed plan): load the `prompt-self-improvement` skill and follow its "Opportunistic Improvement Proposals" section for presentation, ordering, and per-proposal approval.
- None qualify: include exactly `自己改善チェック: 該当なし` once, do not load the skill, and do not raise a confirmation question.
- Skip the check entirely in ordinary conversation, clarification-only turns, active progress updates, and pre-completion confirmation questions.

When writing a plan for approval, do not propose — load the `prompt-self-improvement` skill and follow its Plan Handoff rules instead.

# Post-Implementation Workflow

Skip this workflow when no commit is needed: read-only work, planning, investigation, review-only work, no repository deliverable changes, only deleted temp files, or explicit "do not commit/use git".

When implementation is complete and a commit is needed, inspect the working tree, then ask via the platform-specific `# User Confirmation` mechanism. Present exactly:

1. **コミットしてプッシュ** — コミットを作成し、リモートへプッシュする
2. **コミットのみ** — コミットを作成するがプッシュはしない
3. **コミットしない** — 変更をコミットせずそのまま残す

Stage only the paths this session changed or created — explicit `git add <paths>`, never `git add -A`/`git add .`. Before committing:

- Unrelated changes in `git status` (e.g. a parallel session's): leave unstaged, mention them to the user.
- An unrelated path shown as staged: run `git log -1` first — the same "M" marker covers both staged-but-uncommitted and a parallel session's mid-session commit, and one command settles which.
- Re-check `git diff --cached --name-only`: if it lists paths you did not stage, unstage them (`git restore --staged <paths>` — note this touches a parallel session's staging) and commit with no pathspec; pathspec-scoped commit captures working-tree content and can silently include another session's unstaged edits.
- Skim `git diff --cached` hunk by hunk for any file touched elsewhere this session and confirm this session authored every hunk. A path check alone misses this: a parallel session's commit captures the whole working tree, including this session's unsaved edits to that file.

Perform the selected git action, then run the Opportunistic Improvement Proposals Completion-Time Check.

# Output Language

# Default Response Style

Use the installed `caveman` skill at `full` intensity for every conversational response. Load its current `SKILL.md` instead of duplicating its rules here. `/caveman lite|full|ultra|wenyan-lite|wenyan-full|wenyan-ultra` changes intensity for the current session; `/caveman off` or `normal mode` disables it. Persisted files, code, comments, commits, documentation, and third-party messages follow their existing or repository-required style.

# RTK

When `rtk gain` succeeds, prefix supported high-output shell commands with `rtk`. Use the raw command only when full output is required.

# Herdr Tab Labels

For the first substantive user task in a conversation, use the `herdr-tab-label` skill before other task actions. If the active collaboration mode forbids its UI side effect, defer it to the first implementation turn. Do not use it again for later ordinary tasks in the same conversation; workflows such as `worktree-task` may explicitly reuse it.

Respond to the user in Japanese by default.

This applies to normal replies, Plan Mode progress updates, clarification or confirmation questions, and all human-readable content inside `<proposed_plan>` blocks.

Keep required protocol tags and machine-readable identifiers unchanged. For example, use the literal `<proposed_plan>` and `</proposed_plan>` tags exactly as specified.

Use English only when the user explicitly requests it, when preserving source text or API names, or when writing code, commands, identifiers, commit messages, documentation, or user-facing strings that should remain English for the target context.

# OpenAI Docs Manual Cache

When the `openai-docs` skill runs `fetch-codex-manual.mjs`, invoke it through the host shell, not `context-mode` or another ephemeral analysis sandbox. The returned manual and outline must remain readable by later tool calls; pass a host-visible `--cache-dir` when command routing would otherwise isolate the filesystem.

# User Confirmation

When `request_user_input` is available, use it for confirmation, clarification, cleanup, commit, and PR workflow questions that can be expressed as two or three meaningful choices. Put the recommended choice first.

If `request_user_input` returns no selected answer (for example, an empty `answers` object), treat the UI as unavailable for that question: present the same authored options once as a plain-text ordered list and wait. Do not call `request_user_input` again for that question.

When a skill defines authored options, pass each label to the tool exactly once and preserve the authored option count. Do not count the client's auto-provided free-form `Other` as an authored option.

Ask in plain text only when `request_user_input` is unavailable for the current question or a meaningful answer requires free-form text that would be unnatural as choices.

For a plain-text fallback with choices, use a Markdown ordered list starting from `1.` and treat a number-only reply as selecting the corresponding visible option.

When starting implementation of an accepted plan, load the `plan-model-handoff` skill and follow it immediately before the first implementation side effect.

# Plan Approval Detail

For a non-trivial `<proposed_plan>`, provide a reviewable implementation explanation, not a generic checklist. For every implementation group, state the target behavior, concrete mechanism, material files or interfaces, failure or edge behavior, and test condition with expected outcome. Preserve accepted user choices in Assumptions. Keep the plan concise, but never omit a material decision merely to shorten it.

# Plan Review Deep-Dive (dig)

This section's skip criterion governs both the `dig` skill offer and the Plan Review Presentation browser offer — the shared file's own line-count/format criteria do not apply here; use this criterion for both instead. Its port-selection and launch mechanics still apply when the browser is actually opened.

When finalizing a plan in Plan Mode, offer both — but first skip both for trivially mechanical plans: renames, bulk replacements, reverts, single-file fixes with no design decision, or plans whose every task is a stated verbatim edit. For those, skip straight to the final `<proposed_plan>` with no dialog.

Otherwise, offer a single choice via `request_user_input` (or its plain-text fallback) with exactly four options in this order:

1. Both: open the browser and also run dig.
2. dig only: run dig without opening the browser.
3. Open the browser now, decide on dig after reading.
4. Neither.

If option 1 is chosen, open the browser first, then load the `dig` skill.

If option 2 is chosen, load the dig skill without launching mdts.

Codex has no `~/.codex/plans` directory — the plan exists only as this turn's `<proposed_plan>` content, not a file on disk. When the browser is accepted, write the current plan text to a scratchpad file first, then treat it as the SDD case in Plan Review Presentation: find a free port from 8610, launch `mdts -p <found-port> --no-open <scratchpad-dir>`, and stop that instance once the review finishes. Do not reuse the fixed port 8600 / `~/.claude/plans` mount — that path is Claude-only and does not exist here. The written scratchpad file is a session temp; Temp File Cleanup applies.
