# CLAUDE.md

Guidance for AI coding agents working in this repository. Root `AGENTS.md` is a symlink to this file (Codex reads the same content) — keep instructions platform-neutral (no agent-specific plugin or skill references).

## Repository Overview

Personal dotfiles for Mac and Windows development environments, synchronized via symbolic links.

## User Environment Scope

For environment-specific work, unless explicitly requested, target only macOS, Herdr (not tmux), zsh, Ghostty, Homebrew, and Worktrunk. Do not add, run targeted validation for, or manually verify support outside this environment. Retain existing Windows and tmux assets; change or test them only when explicitly targeted. Treat shared modules under `shell/tmux/` by their active consumer; the directory name alone does not make them tmux assets.

## Repository Branch Policy

Implementation work may start directly on `main`/`master`; when a workflow or skill requires explicit consent for that, treat this section as standing consent. It covers only starting implementation in place — never skip separately required confirmation flows for destructive or side-effecting operations (commits, pushes, pull requests, deletes, deployments, external API writes).

Multiple agent sessions can run against this repository concurrently (e.g. one session renaming a function while another writes new code that calls it). Immediately before committing, refresh the tracking ref with `git fetch origin "+refs/heads/<branch>:refs/remotes/origin/<branch>"` and compare against `origin/<branch>`; if the remote has commits not yet in the local history, inspect them (`git log`/`git show`) for overlap with files this session touched before committing, since a same-file dependency (a rename one session made vs. a call site another session wrote) can integrate correctly by coincidence or silently break.

## Structured Configuration Transformations

For structured configuration transformations, stop on failure (`set -e` or explicit error handling), validate the complete temporary output with the relevant parser, and replace the target only after validation succeeds. Never replace a target with output from a failed transformation.

## CLAUDE.md Maintenance

At implementation completion, before the commit confirmation in the post-implementation flow — so an approved change lands in the same commit — check whether the work surfaced repository knowledge that materially changes how future work should be performed.

- Qualifies: architecture or workflow changes, durable conventions or pitfalls, operational commands, statements the work proved stale or contradicted. Excluded: isolated interactive aliases, implementation details discoverable from source.
- If something qualifies, draft the addition or correction, present it to the user for approval, and edit this file only once approved — never silently.
- Put knowledge needed only when changing one named tool or integration and its owned files in a matching project skill. Put knowledge used across multiple independent integrations or repository-wide lifecycle work in this file. When working in a skill-covered domain, read its `SKILL.md` first.
- If nothing qualifies, propose nothing.

## Key Commands

### Initial Setup
```bash
# Mac
cd mac && ./initialize

# Windows (PowerShell)
cd windows && ./initialize.ps1
```

### Update Environment
```bash
# Mac
cd mac && ./update

# Windows (PowerShell)
cd windows && ./update.ps1
```

### Homebrew Package Management
```bash
cd mac && brew bundle
```

### Run Tests

Whenever you change anything in this repository, run the tests covering what you changed before reporting the work complete — implementation, prompt sources, generated outputs, and configuration alike. This is not optional, and it applies to changes that look too small or too declarative to break a test: this repository pins prompt text, generated-file composition, and config structure in tests, so edits to a `.md`, `.json`, or `.toml` file break tests as readily as code does.

When a change intentionally alters behavior a test pins, update that test in the same task. Leaving it is what produced the stale expectations found later — an implementation deliberately changed while its test kept asserting the old value, so the suite stayed red and the failure stopped carrying information.

```bash
python3 tests/run_tests.py
```
For ordinary implementation changes, run only the tests owned by the files changed in the task:
```bash
python3 tests/run_tests.py --paths <repo-relative changed paths>
```
Fix targeted failures, or report them explicitly at the commit confirmation. Run the full suite only when changing the runner, test layout, `tests/support.py`, `tests/dependencies.toml`, or when explicitly requested. Never leave a suite that was run red.

Main-suite tests mirror their primary implementation owner: `tests/<normalized source parent>/test_<source name>[__scenario].py`. Python source names omit `.py`; other extensions remain encoded in the test name. A test that exercises several files stays with the entrypoint or canonical source that owns its behavior; do not add ordinary ownership to a map.

A new test directory needs an `__init__.py`. Without one the runner reports `Selected 0 tests from 1 test modules` and still exits successfully, so a new test file silently never runs — confirm the expected test count after adding the first file in a directory.

`tests/dependencies.toml` is for proven exceptional dependencies only. When a wider run reveals a failing test omitted by targeted selection, first confirm that a changed source caused the failure, then propose an exact source-to-test entry. After approval, add it and verify that `--paths <source>` selects the test. Do not record unrelated or pre-existing failures. If a valid changed path has no mapped test, the runner reports it and exits successfully; state that omission in the handoff.

The runner executes deterministic test-ID shards in parallel. Tests must be order-independent, must not write shared tracked state, and must use temporary directories for filesystem mutations. Use `python3 tests/run_tests.py --jobs 1` or `python3 -m unittest discover -s tests` for sequential diagnosis.

`tests/shell/tmux/test_<name>_sh.py` tests shell functions by sourcing the `.sh`, invoking functions via `bash -c`, and asserting stdout/status; follow `tests/shell/tmux/test_ai_notification_summary_sh.py`'s `run_fn` pattern. Use this style so `unittest discover` collects new shell-function tests; standalone `.sh` tests are ignored.

When a test pins an exclusion (e.g. `assertNotIn`, a must-not-subscribe list), state the reason in an adjacent comment — an unexplained negative pin forces a later session to rediscover the rejection through history archaeology, or to re-attempt the rejected approach.

Before changing notification hooks or their tests (`ai/*/hooks/`, `shell/tmux/ai_notification_*`), read `.claude/skills/ai-notification-hooks/SKILL.md` — it defines required domain tests beyond the main suite.

### Regenerate AI Prompts

Canonical source-to-command mapping for regenerating committed outputs. The full init scripts (`mac/initialization/ai/{claude,gemini,codex}.sh`) cover everything; the targeted commands below are faster.

| Edited source | Regenerate with |
| --- | --- |
| `ai/common/prompt_base.md` (Claude/Gemini load it at runtime via `@file`) | Codex only: `zsh -c 'source mac/scripts/common.sh && generate_codex_agents'` |
| `ai/common/genshijin-activate.md` (upstream-synced by `sync_genshijin_rule`; keep local edits out of it — put overrides in `genshijin-file-policy.md`), `ai/common/genshijin-file-policy.md` | None — loaded at runtime via `@file` by Claude/Gemini only; Codex does not consume them |
| `ai/codex/codex_base.md` | `zsh -c 'source mac/scripts/common.sh && generate_codex_agents'` |
| Shared-core skill sources (`ai/common/*_core.md`, `ai/{codex,gemini}/skills/*/skill_head.md`/`skill_tail.md`; includes pr-review-subagents skill adapters) | `zsh -c 'source mac/scripts/common.sh && verify_ai_skill_generation_idempotency'` |
| pr-reviewer agent sources (`ai/common/pr_review_subagents/intro_*.md`, `ai/common/pr_review_subagents/format_*.md`, `ai/*/agents_src/`) | `zsh -c 'source mac/scripts/common.sh && generate_pr_reviewer_agents <platform>'` |
| pr-review verifier sources (`ai/common/pr_review_subagents/verifier_core.md`, `ai/*/agents_src/pr_review_verify/`) | `zsh -c 'source mac/scripts/common.sh && verify_pr_review_verifier_agent_generation_idempotency'` (regenerates and verifies) |
| config-audit auditor sources (`ai/common/config_audit_subagents/`, `ai/*/agents_src/config_audit/`) | `generate_config_auditor_agents <platform>` from `mac/scripts/common.sh` |
| review-fix subagent sources (`ai/common/review_fix_subagents/`, `ai/codex/agents_src/review_fix/`) | `zsh -c 'source mac/scripts/common.sh && verify_review_fix_agent_generation_idempotency'` (regenerates and verifies) |
| audit-fix subagent sources (`ai/common/audit_fix_subagents/`, `ai/*/agents_src/audit_fix/`) | `zsh -c 'source mac/scripts/common.sh && verify_audit_fix_agent_generation_idempotency'` (regenerates and verifies all three platforms) |

### External Identifiers

Before adding an externally-sourced identifier (a plugin ID, marketplace name, package name, repo slug) to a declarative config from a blog post, README, or other secondary source, verify it against the primary source (e.g. the target repo's `marketplace.json`/`package.json`) rather than copying the secondary source's command verbatim — a marketplace's registered `name` frequently differs from its repo slug, and a wrong ID installs silently disabled rather than failing loudly.

### Evaluating External Tools

When comparing or selecting an external tool to adopt here (CLI, plugin, package, editor extension), check each candidate's maintenance activity and recent third-party assessment before recommending one, and report the dates you found:

- Last commit and last release date, open issue count, archived status — from the primary source (the repo's API or release page), not a summary article.
- Never treat cumulative popularity (stars, download counts) as evidence of current health; it measures accumulated history, not whether the project still works. State star counts as popularity only.
- Note when a candidate is very new (repository age, `0.x` version, low commit count) — that is a maintenance risk to surface, not a disqualifier.
- Prefer secondary sources published within the last 12 months and give their date; for older ones, state the age and discount accordingly. When a source's author also authored a compared candidate, say so and discount accordingly.

### Removing External Tools

When removing or replacing a tool whose configuration was installed outside this repository (browser extension styles, GUI app preferences, OS-level settings), enumerate those external copies in the plan and state whether each needs manual removal by the user. Deleting the repository source or its setup instructions does not deactivate an already-installed copy. Migrating from mdts to mdv hit exactly this: `mdts-plans.user.css` stayed active in the Stylus extension and, being scoped to `domain("localhost")` rather than a port, kept restyling mdv until it was removed by hand.

## Architecture

### Directory Structure
- `/ai/` - AI assistant configurations (Claude, Gemini, Serena)
- `/mac/` - macOS configurations, initialization, and update scripts
- `/windows/` - Windows configurations and scripts
- `/vimfiles/nvim/` - Neovim configuration (lazy.nvim)
- `/shell/zsh/` - Zsh configuration with znap plugin manager
- `/submodules/` - znap plugin manager (git submodule); other Zsh plugins are downloaded by znap at runtime
- `/gitfiles/` - Git configurations (gitui, lazygit, gh-dash)
- `/terminal/` - Terminal emulator configs (ghostty, etc.)

### Symlink Strategy
Initialize scripts symlink repository files to system locations; core utility functions live in `shell/zsh/alias/utils.zsh`:
- `make_symlink` - Idempotent symlink creation (skips if already correct)
- `smart_copy` - Diff-aware file copy with interactive overwrite prompt
- `smart_merge_json` - Deep-merge JSON files with conflict resolution (supports overwrite, keep, merge-with-priority)

When adding a managed symlink, apply it to the live environment and verify it with `readlink`; if the target exists unexpectedly, stop and report it instead of overwriting it.

Generated agents are symlinked per file into `~/.claude/agents/`, `~/.gemini/agents/`, and `~/.codex/agents/`; init/update only add links, so removing or adding a generated agent in the repository requires manually deleting the stale live link (it dangles otherwise) or creating the new one.

When adding a new initialization step to `mac/initialization/`, `mac/updates/`, or `mac/scripts/ai/` setup functions, ask the user whether re-running it on an already-initialized environment should skip the step (an idempotency guard) before implementing it — a step that re-runs unconditionally can corrupt state it already wrote (e.g. duplicate plugin registrations) on a repeated `mac/initialize`.

When editing shell helpers, do not use global variables for temporary return values or cross-call state. Prefer stdout, explicit arguments, or safe assignment into caller-owned `local` variables so parallel shells and nested calls cannot observe stale state.

In zsh, `path` is a special array tied to `PATH`; never use it as a local or temporary variable name in shell helpers.

In zsh, `local` is `typeset`: re-declaring an already-declared variable inside a loop prints its current value to stdout (bash is silent). In a function whose stdout is read via command substitution, declare every local once outside the loop.

In interactive shells, `cd` fires chpwd hooks (their stdout pollutes command substitutions) and is overridden by zoxide's `cd` function which rejects `-q`; shell helpers that cd inside `$(...)` must use `builtin cd -q`.

Files sourced during zshrc init (e.g. `shell/zsh/filter/base.zsh`) must bail out with `return`, never `exit` — `exit` kills the whole shell mid-init with no visible error (a Herdr popup running `zsh -ic` then closes instantly before the `-c` command ever runs).

Key symlinks:
- `ai/claude/_CLAUDE.md` → `~/.claude/CLAUDE.md`
- `ai/gemini/_GEMINI.md` → `~/.gemini/GEMINI.md`
- `ai/codex/_AGENTS.md` → `~/.codex/AGENTS.md`
- `~/.zshrc` loads `shell/zsh/managed.zsh` through a managed loader block
- `vimfiles/nvim` → `~/.config/nvim`
- `gitfiles/.gitconfig` → `~/.gitconfig`

**Worktrunk**: Install from `mac/Brewfile`; `shell/zsh/managed.zsh` manually initializes its shell integration. Never run `wt config shell install`: it edits the managed `~/.zshrc` and creates duplicate integration.

### No Personal Info or Personal Paths
Never hardcode personally identifying information — the user's real name, personal email address, or similar — in committed sources, including metadata fields such as `@author`, `Copyright`, or `package.json` `author`; use a handle (`mkiken`) or omit the field. Likewise never hardcode a user-specific absolute path (e.g. `/Users/<name>/…`, a real home directory, or an account-name-derived path) in committed sources — scripts, tests, fixtures, or config. Use `$HOME`/`~`, `$SET`, a repo-root-relative path, or a clearly generic placeholder (`/Users/testuser/…`) instead. Machine- or account-specific values belong in un-tracked `*.local` files, not the repository.

When moving or removing tmux key bindings, `source-file` does not clear old bindings; explicitly `unbind` old keys and verify the live state with `tmux list-keys`.

Before working on Herdr keybindings or popups (`terminal/herdr/config.toml`, `[[keys.command]]`), read `.claude/skills/herdr-dev/SKILL.md` first — it routes to `references/` files; read the one it points you to.

Claude-specific files (agents, hooks, scripts) are individually symlinked into `~/.claude/`. Claude has no custom slash commands — former commands live as skills under `ai/claude/skills/`.

Skills (`ai/common/skills/`, `ai/{claude,gemini,codex}/skills/`) are symlinked per directory into `~/.<platform>/skills/` via `setup_ai_skills`, so skill edits take effect immediately — except generated `SKILL.md` files, which must be regenerated from their sources (see "Regenerate AI Prompts" under Key Commands). `ai/common/skills/` is the canonical source for skills shared by all three platforms. For selective sharing, keep the canonical skill in `ai/common/shared_skills/<name>/` and add relative directory symlinks only under the intended `ai/<platform>/skills/` directories; `setup_ai_skills` follows those directory symlinks. Keep adapters and generation only for platform-specific tools, inputs, confirmations, or agents. Claude and Codex use selectively shared `worktree-task` and `herdr-tab-label`; all three platforms use the standalone `fact-based` and `write-tests` skills from `ai/common/skills/`. Edit each shared `SKILL.md` directly. The whole `ai/common` directory is also symlinked to `~/.gemini/common` and `~/.claude/common` for runtime file references — Claude and Gemini only; Codex has no `~/.codex/common`. Python modules shared by the platform hooks therefore live in `shell/tmux/` (e.g. `tmux_emoji.py`, `tmux_window_name.py`); hooks reach them because `Path(__file__).resolve()` dereferences the hook symlink back into the repo.

External skills installed for Codex through `npx skills add --agent codex --global` are managed separately in `~/.agents/skills/`, not `~/.codex/skills/`. Verify that destination after installation and update only the intended skill with `npx skills update <skill> --global --yes`.

Repository-local domain-knowledge skills live in `.claude/skills/<name>/SKILL.md` (currently `herdr-dev`, `ai-notification-hooks`, `claude-plugin-management`); each `.agents/skills/<name>` is a committed relative symlink to the **directory**, so Codex discovers them too and any new subdirectory is visible without touching the symlink. No build step — edit the `.claude/skills/` source directly (frontmatter must stay in the cross-platform subset: `name` + `description` only, no runtime includes). A skill body over 8,192 bytes may split sections with distinct activation conditions into a router `SKILL.md` and `references/*.md`; keep the router at or below 8,192 bytes. Because repo-local skills have no runtime include directive, state each reference path in both forms (`.claude/skills/<name>/references/…` and `.agents/skills/<name>/references/…`). `herdr-dev` is the only skill using this today; the others stay single-file.

`ai/{claude,gemini}/settings.json` are deep-merged, not symlinked, via `smart_merge_json`; live files retain machine-local keys and diverge. Repository edits take effect only via `mac/initialization/ai/{claude,gemini}.sh`, `mac/update`, or manual merge. Merge only adds/updates keys, so repository deletions (e.g. hook registrations) must also be removed manually from live settings.

`ai/codex/config.toml` is also not symlinked: full Codex initialization and update merge it into `~/.codex/config.toml` via `smart_merge_toml`. Editing only the repository source does not update the live file. For a targeted immediate update, run the interactive merge directly: `zsh -c 'source mac/scripts/common.sh && smart_merge_toml "${Repo}ai/codex/config.toml" "$HOME/.codex/config.toml"'`. Do not run this interactive command non-interactively: its safe default keeps the destination unchanged. In that context, inspect the target key, apply only the verified change, and parse the live TOML afterward.

### AI Configuration Generation
Throughout this section: edit the sources, never the generated committed outputs — regenerate via the "Regenerate AI Prompts" table under Key Commands.

Both `_CLAUDE.md` and `_GEMINI.md` are static files using `@file` import syntax to compose prompts from shared source files at runtime:
- **Claude** (`ai/claude/_CLAUDE.md`): `@../common/prompt_base.md` + `@../common/genshijin-file-policy.md`; the plugin supplies the upstream genshijin rule
- **Gemini** (`ai/gemini/_GEMINI.md`): `@common/prompt_base.md` + `@common/genshijin-activate.md` + `@common/genshijin-file-policy.md` + inline Language rules

Edit these sources directly — no build step. Gemini additionally merges `ai/common/mcp.json` (and `mcp.local.json` if present) into its `settings.json`.

- **Codex** (`ai/codex/_AGENTS.md`): Codex's AGENTS.md does not support `@file` imports, so `mac/initialization/ai/codex.sh` (and `mac/updates/codex.sh`) generates `_AGENTS.md` by `cat`-concatenating `ai/common/prompt_base.md` + `ai/codex/codex_base.md`; the generated file is committed and symlinked to `~/.codex/AGENTS.md`. Codex does not receive the genshijin sources — unlike Claude and Gemini, it has no genshijin persona layer. `tests/mac/scripts/test_common_sh__codex_agents_sync.py` pins this two-file composition.

`ai/common/characters/` is an inactive, swappable persona palette. No platform loads it by default; hestia, mizuki_himeji, nagato_yuki, reimu, rikka_takanashi, and nyaruko remain available for an explicit future swap.

Shared-core skills follow one pattern: the skill body lives in core file(s) under `ai/common/`, loaded at runtime by Claude (`` !`/bin/cat ~/.claude/common/<core>.md` `` in the skill) and Gemini (`!{cat ~/.gemini/common/<core>.md}` in the command), and concatenated at build time by `generate_codex_skills` into the committed `ai/codex/skills/<name>/SKILL.md` (`skill_head.md` + core file(s) in listed order + `skill_tail.md` if present). When a Gemini adapter must stay a *skill* rather than a command (for keyword auto-activation), its `SKILL.md` is likewise build-time generated by `generate_gemini_skills` — Gemini skill files support no runtime inclusion (`!{...}` works only in commands). Platform-specific bits (placeholders, confirmation primitive) live in each platform's adapter (Claude `SKILL.md` / Gemini `.toml` or `skill_head.md` / Codex `skill_head.md`).

| Skill | Core file(s) in `ai/common/` | Notes |
| --- | --- | --- |
| pr-review | `pr_review_core.md` + `pr_review_finding_format.md` | `pr_review_finding_format.md` defines the shared final output format (priority matrix, finding structure, section skeleton, 総合評価) |
| pr-review-subagents | `pr_review_subagents/orchestrator_core.md` + `pr_review_finding_format.md` | reviewer agents are separately generated — see below |
| pr-comment-review | `pr_comment_review_core.md` | |
| pr-comment-implement | `pr_comment_implement_core.md` | |
| pr-comment-post | `pr_comment_post_core.md` + `pr_post_mechanics_core.md` | adapter-head bits: `ITEM_NUMBERS`, `{ai_header}`, confirmation primitive |
| pr-body | `pr_body_core.md` + `pr_body_format.md` | `pr_body_format.md` defines the shared PR body format (section skeleton, drafting rules) — also used by pr-create-by-branch |
| pr-create-by-branch | `pr_create_by_branch_core.md` + `pr_body_format.md` | Claude and Codex only (no Gemini variant); adapter-head bits: `TITLE_ARG`, `TARGET_BRANCH_ARG`, confirmation primitive |
| config-audit | `config_audit_subagents/orchestrator_core.md` | auditor agents are separately generated — see below; findings are decided in the browser report (see Report Servers), not by item numbers in the conversation; the skill audits and reports only — applying the decisions is the separate `audit-fix` skill, so it carries no edit tool (Claude keeps `Write` for `audit.json`/`report.html` but drops `Edit`; Gemini drops `replace`, keeps `write_file`); adapter-head bits: `PLATFORM_NAME`, `SCOPE`, `ENTRY_SCOPE`, `CONFIG_PATHS`, `GENERATED_ENTRY_FILE`, `SOURCE_FILES`, `RUN_DIR`, `platform_key`, confirmation primitive |
| review-merge | `review_merge_core.md` | Claude and Codex only; adapter-head bits: `RUN_DIR` resolution, confirmation primitive |
| review-post | `review_post_core.md` + `pr_post_mechanics_core.md` | Claude and Codex only; adapter-head bits: `RUN_DIR`/`ITEM_NUMBERS`, confirmation primitive |
| review-fix | `review_fix_core.md` | Claude and Codex only; designer/implementer role prompts in `ai/common/review_fix_subagents/` (Claude subagents read them at runtime; Codex agents are build-time generated — see below); adapter-head bits: `RUN_DIR`/`ITEM_NUMBERS`, confirmation primitive, subagent launch primitive |
| audit-fix | `audit_fix_core.md` | applies the items config-audit's browser report marked ✅ 適用する: items with a `diff` mechanically, `diff: null` items (conflict resolutions) through designer/implementer subagents in `ai/common/audit_fix_subagents/` (all three platforms' agents are build-time generated — see below); no worktrees and no commits, because the audited files include un-versioned paths such as `~/.claude/CLAUDE.md`; takes no item numbers — `state.json` is the only selection source; Gemini's adapter is the hand-written command `ai/gemini/commands/audit-fix.toml` (matching config-audit), so it is outside `generate_gemini_skills`; adapter-head bits: `PLATFORM`/`RUN_DIR` resolution, confirmation primitive, subagent launch primitive |
| fact-based | `fact_based_core.md` | Gemini adapter is generated; Claude and Codex use shared standalone `ai/common/skills/fact-based/SKILL.md` |
| write-tests | `skills/write-tests/SKILL.md` | No dedicated core file: the canonical source is the standalone `ai/common/skills/write-tests/SKILL.md` shared by Claude and Codex, and generation strips its frontmatter before concatenating. Gemini adapter is generated |

When changing a skill's core composition or adapter-head bits, update this table in the same commit.

Beyond their shared cores (table above), four skill families have GENERATED, committed subagent definitions, assembled by functions in `mac/scripts/common.sh` (called by the init/update scripts). Subagent definition files support no runtime file inclusion on any platform, hence build-time generation.

- **pr-review-subagents** — 21 reviewer agents (7 dimensions × 3 platforms: `ai/claude/agents/pr-reviewer-*.md`, `ai/gemini/agents/pr-reviewer-*.md`, `ai/codex/agents/pr_reviewer_*.toml`): `generate_pr_reviewer_agents` assembles each from shared dimension fragments (`intro_<dim>.md`, `format_<dim>.md`) plus per-platform `ai/<platform>/agents_src/` files (`head_<dim>`, `rules_<dim>`, `rules_common`). Plus 3 adversarial-verification agents (`pr-review-verifier.md` ×2, `pr_review_verifier.toml`): `generate_pr_review_verifier_agents` assembles each from `ai/common/pr_review_subagents/verifier_core.md` plus `ai/<platform>/agents_src/pr_review_verify/head_verifier`.
- **config-audit** — 18 auditor agents (6 dimensions × 3 platforms: `config-auditor-*.md` / `config_auditor_*.toml` in the same `agents` dirs): `generate_config_auditor_agents` assembles each from `ai/common/config_audit_subagents/` fragments (`intro_<dim>.md`, shared `rules_common.md`, `format_<dim>.md`) plus per-platform `ai/<platform>/agents_src/config_audit/head_<dim>` files.
- **review-fix** — 2 Codex agents (`ai/codex/agents/review_fix_{designer,implementer}.toml`): `generate_review_fix_agents` (arg-less, Codex-only) assembles each from `ai/common/review_fix_subagents/<role>_core.md` plus `ai/codex/agents_src/review_fix/head_<role>.toml`. Claude has no generated counterpart — its ad-hoc Task subagents read the same role cores from `~/.claude/common/review_fix_subagents/` at runtime.
- **audit-fix** — 6 agents (2 roles × 3 platforms: `ai/{claude,gemini}/agents/audit-fix-{designer,implementer}.md`, `ai/codex/agents/audit_fix_{designer,implementer}.toml`): `generate_audit_fix_agents <platform>` assembles each from `ai/common/audit_fix_subagents/<role>_core.md` plus `ai/<platform>/agents_src/audit_fix/head_<role>`. Unlike review-fix, **Claude agents are generated too** rather than reading the role cores at runtime, because the frontmatter is what pins each role's model — designer on the strong model (Claude `opus` / Gemini `gemini-2.5-pro` / Codex `model_reasoning_effort = "high"`), implementer on the cheap one (Claude `sonnet` / Gemini `gemini-2.5-flash` / Codex `"low"`). The orchestrator skill runs on `sonnet` while `config-audit` runs on `fable`; that split is the whole reason audit-fix exists as a separate skill, and an ad-hoc `general-purpose` Task subagent would inherit the caller's model and erase it.

Standalone skills (no shared core, hand-maintained): `web-summary` — Claude `ai/claude/skills/web-summary/SKILL.md` and Gemini `ai/gemini/commands/web-summary.toml` are a manually synchronized pair with no generator (editing one does not update the other); `prompt-self-improvement` — single shared source in `ai/common/skills/`, symlink-deployed to all three platforms; `herdr` — single shared source in `ai/common/skills/`, symlink-deployed to all three platforms, vendored from the official herdr `SKILL.md` (teaches an agent to operate the `herdr` CLI from inside a Herdr-managed pane; guarded by a `HERDR_ENV=1` check so it is a no-op outside Herdr); `grilling` — Claude `ai/claude/skills/grilling/SKILL.md` and Codex `ai/codex/skills/grilling/SKILL.md` are a manually synchronized pair with no generator, adapted from Matt Pocock's MIT-licensed upstream; the two differ only in confirmation primitive (`AskUserQuestion` vs `request_user_input`) and persistence target (plan file vs `<proposed_plan>` text). Paired with `dig` as the fixed two-stage Plan Review Deep-Dive — never offer one without the other.

### Report Servers

`review-merge` and `config-audit` both present their findings as an HTML report served over loopback, where the user decides each item and the browser POSTs the result to `<RUN_DIR>/state.json`; a follow-up step then reads that file — `review-fix`/`review-post` for the review flow, the separate `audit-fix` skill for the audit flow. Scripts live in `shell/common/pr/` (symlinked to `~/.config/ai-pr/bin` by `setup_ai_pr_tools`, which globs `*.sh`/`*.py` — a new script there needs no init/update change).

`serve_review_report.py` is shared by both flows and picks a profile from the run directory's manifest: `merged.json` → review (`schema_version` 2, decisions `fix`/`post`/`dismiss`), `audit.json` → audit (`schema_version` 1, decisions `apply`/`dismiss`). The generators stay separate (`generate_review_report.py`, `generate_audit_report.py`) because the review report is built around PR data — `gh` lookups, GitHub links, per-AI badges — that an audit has no counterpart for. When adding a decision value or a manifest field, update the profile in the server, the generator's tables, and the core md together; the contract tests under `tests/ai/common/*/` pin exactly that agreement.

The agent always starts the server without `--open`, verifies the URL responds, then opens it once; the `review-report` / `audit-report` zsh functions pass `--open` instead, because no agent is there to verify. `state.json` is browser-owned — no skill ever writes it.

### Claude Hooks
Notification-hook roles and implementation rules for all three platforms live in `.claude/skills/ai-notification-hooks/SKILL.md` — read it before changing `ai/*/hooks/` or `shell/tmux/ai_notification_*`.

### Plugin Management

**Zsh (znap)**: Config in `shell/zsh/plugin.zsh`. Plugins updated via `znap pull` in `mac/update` (submodule/runtime split: see Directory Structure).

**Neovim (lazy.nvim)**: Plugins in `vimfiles/nvim/lua/plugins/`. VSCode Neovim uses separate `plugins_vscode/`. Updated via `nvim --headless "+Lazy! sync | TSUpdate" +qa` in `mac/update`.

**Herdr integrations**: before changing Herdr integration (`mac/scripts/herdr.sh`, Herdr plugins such as notify-rich, Gemini's Herdr notification split, shell status icon mirroring), read `.claude/skills/herdr-dev/SKILL.md`. Never run `herdr integration install` against live Claude or Codex configuration; always use the repository helper.

**Claude Code plugins**: before adding, updating, or removing a Claude Code plugin (`mac/scripts/ai/claude.sh` setup functions, `ai/claude/settings.json` `enabledPlugins`/`extraKnownMarketplaces`, or their call sites in `mac/initialization/ai/claude.sh` and `mac/updates/claude.sh`), read `.claude/skills/claude-plugin-management/SKILL.md`.

## AI Prompt File Editing

When editing AI prompt files in this repository:

- **Default to English** for new or modified content (reduces token consumption); if the original file uses a different language, follow it (e.g. Japanese character dialogue examples)
- **Keep skill prose non-genshijin**: skill sources and generated skill outputs always follow their existing normal prose style. Do not ask whether to use genshijin when editing a skill, even though `SKILL.md` is a text file.
- **Write concisely**: as concise as meaning and intent allow — every loaded prompt consumes context. When condensing existing files, follow `ai/common/prompt_shortening_guide.md`.
- **Runtime loading differs per platform**: Claude Code and Gemini CLI load only the markdown body of agent/skill files as the prompt — frontmatter (including YAML `#` comments) costs zero runtime tokens. Codex instead injects the whole SKILL.md raw at invocation, so every Codex skill frontmatter line counts as prompt cost. Codex agent TOML files are parsed; `#` comments there cost nothing.
- **GENERATED-file notices** are placed where they cost no runtime tokens: YAML frontmatter comments for Claude/Gemini `pr-reviewer-*.md`, a `#` comment for Codex `pr_reviewer_*.toml`. Codex `SKILL.md` files intentionally carry no notice (raw injection would bill it) — the adjacent `skill_head.md` sources and this file are the edit guard. Do not add visible-body notices to generated files.
- **Verify regeneration before committing generated outputs**: for shared-core skills, use `verify_ai_skill_generation_idempotency` from the regeneration table; it generates twice and fails if any SHA-256 changes. For other generators, after updating sources and running the generator once, record each generated output's hash, re-run the generator, and confirm the hash is unchanged. The output may legitimately differ from `HEAD`; review that diff separately. A changed hash on the second run means the first output was stale or generation is not idempotent.
- **`opusplan` vs. manual `/model` override**: `ai/claude/settings.json` sets `"model": "opusplan"`, which auto-switches Opus during plan mode and Sonnet during implementation. A manual `/model fable` (or any other explicit model) overrides `opusplan` for the rest of the session — plan and implementation both stay on that model with no auto-switch. `ai/claude/_CLAUDE.md`'s "Fable Model Check After Plan Approval" section detects this specific case (session left on Fable) and offers a model choice, right after plan approval, before implementation starts.

## Commit Message Convention

A `commit-msg` hook enforces commitizen (czg) + commitlint; non-conforming commits are rejected.

### Format

```
<type>(<scope>): <emoji> <subject>
```

Example: `perf(claude): ⚡ pr-review-subagentsスキルで止まりにくくする`

### Allowed Types and Scopes

The canonical source is `.commitlintrc.json`:
- Types: `rules.type-enum`
- Scopes: `rules.scope-enum`

Do not duplicate the allowed lists here. When changing types or scopes, update `.commitlintrc.json` first; align `.czrc` type prompts only when type values change.

### Rules

- **scope is required** — empty scope will be rejected
- **subject**: 1–50 characters, must NOT start with an uppercase letter
- **emoji**: czg auto-prepends it; manual commits must include the appropriate emoji at the start of the subject
- **body**: 1行100文字以内に折り返す（`body-max-line-length` は commitlint 既定値で有効。`.commitlintrc.json` に明示エントリは無い）。日本語本文は超過しやすい
