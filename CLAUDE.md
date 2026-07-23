# CLAUDE.md

Guidance for AI coding agents working in this repository. Root `AGENTS.md` is a symlink to this file (Codex reads the same content) — keep instructions platform-neutral (no agent-specific plugin or skill references).

## Repository Overview

Personal dotfiles for Mac and Windows development environments, synchronized via symbolic links.

## Repository Branch Policy

Implementation work may start directly on `main`/`master`; when a workflow or skill requires explicit consent for that, treat this section as standing consent. It covers only starting implementation in place — never skip separately required confirmation flows for destructive or side-effecting operations (commits, pushes, pull requests, deletes, deployments, external API writes).

Multiple agent sessions can run against this repository concurrently (e.g. one session renaming a function while another writes new code that calls it). Immediately before committing, run `git fetch origin <branch>` and compare against `origin/<branch>`; if the remote has commits not yet in the local history, inspect them (`git log`/`git show`) for overlap with files this session touched before committing, since a same-file dependency (a rename one session made vs. a call site another session wrote) can integrate correctly by coincidence or silently break.

When a file mixes this session's changes with another session's unrelated in-progress edits, and only this session's hunks are staged (e.g. via a rebuilt index blob), do not run `git commit -- <paths>`: pathspec-scoped commit ignores the partially staged index for that path and instead commits the working tree's current content, silently pulling in the other session's unstaged changes. Verify `git diff --cached` matches intent, then commit with no pathspec.

## CLAUDE.md Maintenance

At implementation completion, before the commit confirmation in the post-implementation flow, check whether the work surfaced repository knowledge that materially changes how future work should be performed: architecture or workflow changes, durable conventions or pitfalls, operational commands, or existing statements the work proved stale or contradicted. Do not add isolated interactive aliases or implementation details that are readily discoverable from source. If so, draft the addition or correction, present it to the user for approval, and edit this file only when approved — never silently. Proposing before the commit confirmation lets an approved change land in the same commit. If nothing qualifies, propose nothing.

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
```bash
python3 -m unittest discover -s tests
```
Run before committing code changes (the suite takes seconds). Fix failures, or report them explicitly at the commit confirmation — never leave the suite red.

Shell functions (e.g. those in `shell/tmux/ai_notification_*.sh`) are unit-tested from Python: a `tests/test_*.py` `source`s the `.sh` and invokes the function via `bash -c`, asserting on stdout and the return code (see `tests/test_ai_notification_summary.py` for the `run_fn` helper pattern). Write new shell-function tests in this style so `unittest discover` collects them — a standalone `.sh` test file is not picked up by the suite.

When changing the notification hooks (`ai/*/hooks/*notification*.sh`, `shell/tmux/ai_notification_*.sh`), additionally run the manual smoke test `bash tests/manual/notification_hook_smoke.sh` — it feeds representative hook events to all three hooks; by default it sends real Mac notifications and updates tmux window icons, so it is kept out of unittest discovery. Pass `--silent` (sets `NOTIFY_SILENT=1`, which overrides even `NOTIFY_FORCE`) to run the same exit-code checks without any notification or tmux icon side effects. AI agents running this smoke test should default to `--silent`; use the no-flag form only when a real-notification/tmux-icon check is explicitly needed.

The Gemini hook's context-alert e2e test lives outside the main discovery path — when changing the Gemini notification hook or `shell/tmux/gemini_context_usage.py`, also run `python3 -m unittest discover -s ai/gemini/hooks/tests`.

The Codex hook unit tests also live outside the main discovery path — when changing `ai/codex/hooks/*.py`, also run `python3 -m unittest discover -s ai/codex/hooks`.

### Regenerate AI Prompts

Canonical source-to-command mapping for regenerating committed outputs. The full init scripts (`mac/initialization/ai/{claude,gemini,codex}.sh`) cover everything; the targeted commands below are faster.

| Edited source | Regenerate with |
| --- | --- |
| `ai/common/prompt_base.md`, `ai/common/characters/*.md` (Claude/Gemini load these at runtime via `@file`) | Codex only: `zsh -c 'source mac/scripts/common.sh && generate_codex_agents'` |
| `ai/codex/codex_base.md` | `zsh -c 'source mac/scripts/common.sh && generate_codex_agents'` |
| Shared-core skill sources (`ai/common/*_core.md`, `ai/{codex,gemini}/skills/*/skill_head.md`/`skill_tail.md`; includes pr-review-subagents skill adapters) | `zsh -c 'source mac/scripts/common.sh && verify_ai_skill_generation_idempotency'` |
| pr-reviewer agent sources (`ai/common/pr_review_subagents/intro_*.md`, `ai/common/pr_review_subagents/format_*.md`, `ai/*/agents_src/`) | `zsh -c 'source mac/scripts/common.sh && generate_pr_reviewer_agents <platform>'` |
| config-audit auditor sources (`ai/common/config_audit_subagents/`, `ai/*/agents_src/config_audit/`) | `generate_config_auditor_agents <platform>` from `mac/scripts/common.sh` |

## Architecture

### Directory Structure
- `/ai/` - AI assistant configurations (Claude, Gemini, Serena)
- `/mac/` - macOS configurations, initialization, and update scripts
- `/windows/` - Windows configurations and scripts
- `/vimfiles/nvim/` - Neovim configuration (lazy.nvim)
- `/shell/zsh/` - Zsh configuration with znap plugin manager
- `/submodules/` - znap plugin manager (git submodule); other Zsh plugins are downloaded by znap at runtime
- `/gitfiles/` - Git configurations (gitui, lazygit, gh-dash, workmux)
- `/terminal/` - Terminal emulator configs (ghostty, etc.)

### Symlink Strategy
Initialize scripts symlink repository files to system locations; core utility functions live in `shell/zsh/alias/utils.zsh`:
- `make_symlink` - Idempotent symlink creation (skips if already correct)
- `smart_copy` - Diff-aware file copy with interactive overwrite prompt
- `smart_merge_json` - Deep-merge JSON files with conflict resolution (supports overwrite, keep, merge-with-priority)

When adding a managed symlink, apply it to the live environment and verify it with `readlink`; if the target exists unexpectedly, stop and report it instead of overwriting it.

When adding a new initialization step to `mac/initialization/`, `mac/updates/`, or `mac/scripts/ai/` setup functions, ask the user whether re-running it on an already-initialized environment should skip the step (an idempotency guard) before implementing it — a step that re-runs unconditionally can corrupt state it already wrote (e.g. duplicate plugin registrations) on a repeated `mac/initialize`.

When editing shell helpers, do not use global variables for temporary return values or cross-call state. Prefer stdout, explicit arguments, or safe assignment into caller-owned `local` variables so parallel shells and nested calls cannot observe stale state.

In zsh, `path` is a special array tied to `PATH`; never use it as a local or temporary variable name in shell helpers.

Files sourced during zshrc init (e.g. `shell/zsh/filter/base.zsh`) must bail out with `return`, never `exit` — `exit` kills the whole shell mid-init with no visible error (a Herdr popup running `zsh -ic` then closes instantly before the `-c` command ever runs).

Key symlinks:
- `ai/claude/_CLAUDE.md` → `~/.claude/CLAUDE.md`
- `ai/gemini/_GEMINI.md` → `~/.gemini/GEMINI.md`
- `ai/codex/_AGENTS.md` → `~/.codex/AGENTS.md`
- `~/.zshrc` loads `shell/zsh/managed.zsh` through a managed loader block
- `vimfiles/nvim` → `~/.config/nvim`
- `gitfiles/.gitconfig` → `~/.gitconfig`

### No Personal Paths
Never hardcode a user-specific absolute path (e.g. `/Users/<name>/…`, a real home directory, or an account-name-derived path) in committed sources — scripts, tests, fixtures, or config. Use `$HOME`/`~`, `$SET`, a repo-root-relative path, or a clearly generic placeholder (`/Users/testuser/…`) instead. Machine- or account-specific values belong in un-tracked `*.local` files, not the repository.

When moving or removing tmux key bindings, `source-file` does not clear old bindings; explicitly `unbind` old keys and verify the live state with `tmux list-keys`.

When adding or changing key bindings in `terminal/herdr/config.toml`, Herdr is an environment independent of tmux — ignore tmux (`.tmux.conf`) bindings even though both share the `ctrl+t` prefix. Do not judge conflicts from the committed `config.toml` alone: it lists only overrides, while Herdr ships ~146 default action bindings (e.g. `prefix+g`=goto, `prefix+shift+g`=new_worktree). Confirm the live default keymap with `herdr --default-config` before choosing a key. Specifically check whether the chosen key already carries a default action absent from `config.toml` (e.g. `prefix+shift+w`=rename_workspace) — since `config.toml` lists only overrides, binding over an unlisted default silently shadows it without showing up as a diff or conflict in the committed file.

When a `[[keys.command]]` popup needs to act on the pane that triggered it (not the popup itself), read `HERDR_ACTIVE_PANE_ID` / `HERDR_ACTIVE_PANE_CWD` — `HERDR_PANE_ID` is unset inside a popup and only identifies the popup pane itself. Confirmed by injecting a probe binding and inspecting `env | grep HERDR` from inside a live popup. `[[keys.command]]` commands also run as children of the herdr server with a stripped `PATH` (`/usr/bin:/bin:/usr/sbin:/sbin`) even though the server's own environment carries the full PATH; `HERDR_ENV=1` and the `HERDR_ACTIVE_*` vars are injected (confirmed by dumping `env` from a live popup). Launch anything that needs user tooling via a login shell (`zsh -ilc "..."`) so `~/.zprofile`'s `brew shellenv` restores PATH — with non-login `zsh -ic`, Homebrew tools are missing during zshrc init (`managed.zsh`'s `brew --prefix` fails and cannot repair PATH either). `herdr pane send-text <pane_id> <text>` takes exactly two positional arguments and does not treat `--` as an end-of-options separator — passing one leaks a literal `--` into the inserted text; pass the two arguments directly.

Claude-specific files (agents, hooks, scripts) are individually symlinked into `~/.claude/`. Claude has no custom slash commands — former commands live as skills under `ai/claude/skills/`.

Skills (`ai/common/skills/`, `ai/{claude,gemini,codex}/skills/`) are symlinked per directory into `~/.<platform>/skills/` via `setup_ai_skills`, so skill edits take effect immediately — except generated `SKILL.md` files (all Codex shared-core skills and Gemini fact-based), which must be regenerated from their sources (see "Regenerate AI Prompts" under Key Commands). The whole `ai/common` directory is also symlinked to `~/.gemini/common` and `~/.claude/common` for runtime file references — Claude and Gemini only; Codex has no `~/.codex/common`. Python modules shared by the platform hooks therefore live in `shell/tmux/` (e.g. `tmux_emoji.py`, `tmux_window_name.py`); hooks reach them because `Path(__file__).resolve()` dereferences the hook symlink back into the repo.

`ai/claude/settings.json` and `ai/gemini/settings.json` are the exception: not symlinked but deep-merged into `~/.claude/settings.json` / `~/.gemini/settings.json` via `smart_merge_json`, and the files diverge (the live files accumulate machine-local keys). Editing the repository source alone does not update the live file — apply with `mac/initialization/ai/{claude,gemini}.sh` / `mac/update`, or merge manually for immediate effect. Merging only adds or updates keys: removing an entry (e.g. deleting a hook registration) never propagates, so also delete it from the live file by hand.

### AI Configuration Generation
Throughout this section: edit the sources, never the generated committed outputs — regenerate via the "Regenerate AI Prompts" table under Key Commands.

Both `_CLAUDE.md` and `_GEMINI.md` are static files using `@file` import syntax to compose prompts from shared source files at runtime:
- **Claude** (`ai/claude/_CLAUDE.md`): `@../common/prompt_base.md` + `@../common/characters/reimu.md`
- **Gemini** (`ai/gemini/_GEMINI.md`): `@../common/prompt_base.md` + `@../common/characters/rikka_takanashi.md` + inline Language rules

Edit these sources directly — no build step. Gemini additionally merges `ai/common/mcp.json` (and `mcp.local.json` if present) into its `settings.json`.

- **Codex** (`ai/codex/_AGENTS.md`): Codex's AGENTS.md does not support `@file` imports, so `mac/initialization/ai/codex.sh` (and `mac/updates/codex.sh`) generates `_AGENTS.md` by `cat`-concatenating `ai/common/prompt_base.md` + `ai/common/characters/nyaruko.md` + `ai/codex/codex_base.md`; the generated file is committed and symlinked to `~/.codex/AGENTS.md`.

`ai/common/characters/` is a swappable persona palette: reimu (Claude), rikka_takanashi (Gemini), and nyaruko (Codex) are currently wired; hestia, mizuki_himeji, and nagato_yuki are intentional alternates kept for swapping, not dead files.

Shared-core skills follow one pattern: the skill body lives in core file(s) under `ai/common/`, loaded at runtime by Claude (`` !`/bin/cat ~/.claude/common/<core>.md` `` in the skill) and Gemini (`!{cat ~/.gemini/common/<core>.md}` in the command), and concatenated at build time by `generate_codex_skills` into the committed `ai/codex/skills/<name>/SKILL.md` (`skill_head.md` + core file(s) in listed order + `skill_tail.md` if present). When a Gemini adapter must stay a *skill* rather than a command (for keyword auto-activation), its `SKILL.md` is likewise build-time generated by `generate_gemini_skills` — Gemini skill files support no runtime inclusion (`!{...}` works only in commands). Platform-specific bits (placeholders, confirmation primitive) live in each platform's adapter (Claude `SKILL.md` / Gemini `.toml` or `skill_head.md` / Codex `skill_head.md`).

| Skill | Core file(s) in `ai/common/` | Notes |
| --- | --- | --- |
| pr-review | `pr_review_core.md` + `pr_review_finding_format.md` | `pr_review_finding_format.md` defines the shared final output format (priority matrix, finding structure, section skeleton, 総合評価) |
| pr-review-subagents | `pr_review_subagents/orchestrator_core.md` + `pr_review_finding_format.md` | reviewer agents are separately generated — see below |
| pr-comment-review | `pr_comment_review_core.md` | |
| pr-comment-implement | `pr_comment_implement_core.md` | |
| pr-comment-post | `pr_comment_post_core.md` | adapter-head bits: `ITEM_NUMBERS`, `{ai_header}`, confirmation primitive |
| pr-body | `pr_body_core.md` + `pr_body_format.md` | `pr_body_format.md` defines the shared PR body format (section skeleton, drafting rules) — also used by pr-create-by-branch |
| pr-create-by-branch | `pr_create_by_branch_core.md` + `pr_body_format.md` | Claude and Codex only (no Gemini variant); adapter-head bits: `TITLE_ARG`, `TARGET_BRANCH_ARG`, confirmation primitive |
| config-audit | `config_audit_subagents/orchestrator_core.md` | auditor agents are separately generated — see below; adapter-head bits: `PLATFORM_NAME`, `SCOPE`, `ENTRY_SCOPE`, `CONFIG_PATHS`, `GENERATED_ENTRY_FILE`, `SOURCE_FILES`, confirmation primitive |
| fact-based | `fact_based_core.md` | Gemini adapter is a generated skill (not a command); Claude adapter keeps `$ARGUMENTS` handling in head/tail around the runtime include |

When changing a skill's core composition or adapter-head bits, update this table in the same commit.

Beyond their shared cores (table above), two skill families have GENERATED, committed subagent definitions, assembled by functions in `mac/scripts/common.sh` (called by the init/update scripts). Subagent definition files support no runtime file inclusion on any platform, hence build-time generation.

- **pr-review-subagents** — 21 reviewer agents (7 dimensions × 3 platforms: `ai/claude/agents/pr-reviewer-*.md`, `ai/gemini/agents/pr-reviewer-*.md`, `ai/codex/agents/pr_reviewer_*.toml`): `generate_pr_reviewer_agents` assembles each from shared dimension fragments (`intro_<dim>.md`, `format_<dim>.md`) plus per-platform `ai/<platform>/agents_src/` files (`head_<dim>`, `rules_<dim>`, `rules_common`).
- **config-audit** — 18 auditor agents (6 dimensions × 3 platforms: `config-auditor-*.md` / `config_auditor_*.toml` in the same `agents` dirs): `generate_config_auditor_agents` assembles each from `ai/common/config_audit_subagents/` fragments (`intro_<dim>.md`, shared `rules_common.md`, `format_<dim>.md`) plus per-platform `ai/<platform>/agents_src/config_audit/head_<dim>` files.

Standalone skills (no shared core, hand-maintained): `web-summary` — Claude `ai/claude/skills/web-summary/SKILL.md` and Gemini `ai/gemini/commands/web-summary.toml` are a manually synchronized pair with no generator (editing one does not update the other); `prompt-self-improvement` — single shared source in `ai/common/skills/`, symlink-deployed to all three platforms; `herdr` — single shared source in `ai/common/skills/`, symlink-deployed to all three platforms, vendored from the official herdr `SKILL.md` (teaches an agent to operate the `herdr` CLI from inside a Herdr-managed pane; guarded by a `HERDR_ENV=1` check so it is a no-op outside Herdr); `skill-creator` and `write-tests` — Claude-only, in `ai/claude/skills/`.

### Claude Hooks
`ai/claude/hooks/` contains notification hooks symlinked into `~/.claude/hooks/` (Gemini/Codex follow the same split):
- `claude-hook.py` - Sets the in-progress tmux window icon (🤖) and removes icons on SessionEnd
- `stop-send-notification.sh` - Owns Notification / Stop / StopFailure events: sets the tmux icon immediately on event detection for Notification (✋) / StopFailure (❌), then sends a rich Mac notification after transcript analysis. Icons are set directly (not via `notify --tmux-icon`) so they appear before the slow summary generation. For Stop, the ✅ icon and completion notification are deferred until after transcript analysis and are skipped entirely while background work is pending (`PENDING_BACKGROUND_WORK` from `claude_transcript_analyze.py`: async agents launched but not yet notified, or an armed ScheduleWakeup) — Stop fires at every turn end, and its hook input carries no background-task fields, so the transcript is the only signal. StopFailure fires when a turn aborts on an API error or a malformed tool call (Stop does NOT fire then) — without this registration such failures are silent.
- When one hook emits both a macOS notification and tmux state for the same event, complete the tmux update synchronously before calling `notify`. Use strict error reporting so tmux failures reach the hook error log without blocking the Mac notification, and cover the ordering with isolated tests.
- Shared shell header for the three platform notification hooks (sources + `NOTIFY_FORCE` + `debug_log`): `shell/tmux/ai_notification_hook_common.sh`
- Hooks that intentionally send macOS notifications must set `NOTIFY_FORCE=1` (prefer the shared header) and test delivery with `DISABLE_NOTIFY=1`; ordinary AI-spawned commands must remain suppressed.
- Suppression precedence: `NOTIFY_SILENT` > `NOTIFY_FORCE` > `DISABLE_NOTIFY`. `NOTIFY_SILENT=1` silences both the `notify` gate (`shell/zsh/alias/notification.zsh`) and tmux icon updates (`shell/tmux/tmux_window_name.sh`), overriding even `NOTIFY_FORCE` — used by the smoke test's `--silent` flag so hook-logic verification never produces a real notification or icon change.
- Stateful hooks must define their state scope and test multiple transcripts or agents sharing one session ID so one cannot reset another's state.
- Before referencing a new hook input field, confirm it actually exists: check the official hooks schema, or capture a real event (enable the hook's `DEBUG_ENABLED` log) and inspect the payload. A guard keyed to a nonexistent field degrades silently — the `background_tasks` Stop guard shipped dead and went unnoticed for weeks.
- Hook critical paths: python3 startup costs ~45ms vs ~7ms for jq/date on this machine — add a python3 process only when it replaces many subprocess launches; otherwise fold work into an existing jq query or pure bash, and benchmark baseline vs candidate before restructuring.
- Benchmarking hooks: `/bin/bash` is 3.2 (no `EPOCHREALTIME`); time hook benchmarks with perl `Time::HiRes` or zsh.
- A hook test's `run_hook`-style helper must not pass `os.environ.copy()` straight through: pop `HERDR_ENV`/`TMUX`/`TMUX_PANE` first. Hooks early-return under these guards (e.g. `codex-stop-notification.sh`'s `HERDR_ENV` check), so a test running inside such an environment silently short-circuits the hook under test instead of exercising it — see `tests/test_herdr_setup.py`'s `run_zsh` for the reference pop pattern.

### Plugin Management

**Zsh (znap)**: Config in `shell/zsh/plugin.zsh`. Plugins updated via `znap pull` in `mac/update` (submodule/runtime split: see Directory Structure).

**Neovim (lazy.nvim)**: Plugins in `vimfiles/nvim/lua/plugins/`. VSCode Neovim uses separate `plugins_vscode/`. Updated via `nvim --headless "+Lazy! sync | TSUpdate" +qa` in `mac/update`.

**GSD Core**: `setup_gsd_core_for_runtime` installs `@opengsd/gsd-core@latest` for Claude Code and Codex with the `standard` profile and portable hooks. `@opengsd/gsd-core` itself has no install/update distinction — every invocation is a full (re-)install with identical arguments and writes hooks.json/settings.json again; `install` vs `update` here is purely this repo's own VERSION-file guard around whether to re-run that `npx` call, not a gsd-core concept. That guard only skips the `npx` re-run (to avoid duplicate hook groups on repeat installs); the symlink reconciliation (`_restore_managed_codex_gsd_hooks`) and the Claude permission fix always run regardless of the guard, so a previously materialized real `hooks.json` file is restored to the managed symlink on any subsequent install/update — this keeps Herdr's `_herdr_live_config_ready` (which requires the Codex `hooks.json` to be a symlink) satisfied. Generated assets stay under the home directory and are not vendored here. The Codex installer replaces the managed `~/.codex/hooks.json` symlink and emits machine-specific commands. Before restoring the symlink, the setup helper normalizes only exact absolute GSD commands rooted at the current home, removes only exact duplicate GSD hook objects, and requires the full result to match `ai/codex/hooks.json`. Foreign-home commands and unknown or missing hooks, including the Herdr registration, stop the update and preserve the generated file for review. Do not use Codex local or custom staging installs: they write generated skills containing absolute paths into `~/.agents/skills`. The Claude installer appends `Write(.planning/*)` and `Write(STATE.md)` permission rules that new Claude Code rejects (only `Edit(path)` rules cover file-editing tools), so the setup helper post-processes the live `~/.claude/settings.json`, rewriting those two entries to their `Edit(...)` equivalents. It shows the proposed diff and asks for confirmation before applying (skips silently when there is no change; leaves the file untouched if declined), and writes in place with jq (no `--sort-keys`) to preserve the smart-merge-managed key order and machine-local keys.

**Herdr integrations**: `mac/scripts/herdr.sh` runs the official Claude and Codex installers in isolated staging, validates their registrations against the managed configuration, then transactionally deploys the hook scripts. Never run `herdr integration install` against live Claude or Codex configuration, especially the managed `~/.codex/hooks.json`; always use the repository helper. Gemini has no installer integration and relies only on Herdr's screen-manifest detection. This is the herdr→AI direction (detection/state reporting); the reverse AI→herdr direction (an agent driving the `herdr` CLI) is a separate concern handled by the vendored `ai/common/skills/herdr/SKILL.md` (see Standalone skills above). `sync_herdr_skill` (`mac/scripts/common.sh`), called once from `mac/updates/claude.sh` before `setup_ai_skills`, pulls the upstream `SKILL.md` on every `mac/update` and overwrites the vendored copy on a diff — but never stages it, so a human always reviews the change via `git diff` before committing. Herdr runs `[[events]]` plugin hooks with the same stripped `PATH` as `[[keys.command]]` popups — no Homebrew dirs, `python3` is the system 3.9, `jq` is macOS's `/usr/bin/jq`, and `herdr` itself resolves only via the injected `HERDR_BIN_PATH` — so Homebrew-only tools like `terminal-notifier` silently vanish (tab renames kept working while every Mac notification failed for a day); the plugin therefore appends the Homebrew bin dirs to `PATH` (append, not prepend, so test `fake_bin` stubs keep precedence). When debugging a plugin, check `herdr plugin log list --plugin <id>` first — it records each invocation's stderr and exit code; reproducing in your own full-`PATH` shell proves nothing about the hook environment. After editing a linked plugin's `herdr-plugin.toml`, neither `herdr server reload-config` nor `herdr plugin disable`/`enable` reloads its manifest; run `herdr plugin unlink <id>` followed by `herdr plugin link <path>`, then verify events and warnings with `herdr plugin list --plugin <id> --json`.

Gemini opts OUT of `notify-rich` entirely (notification AND tab rename — see the `agent=="gemini"` guard near the top of `notify-on-agent-status.sh`), because its `agent_status` is derived solely from screen-manifest detection and oscillates `done`↔`working`↔`idle`, firing the plugin's notification gate many times per response and flooding Mac notifications. Gemini instead notifies via its own `AfterAgent`/`Notification` tmux hooks (`ai/gemini/hooks/notification.sh`), whose `IN_HERDR` guard around the notification body was relaxed so it fires under Herdr too (the ToolPermission filter for the `notification` event still applies under Herdr; only the tmux-icon calls stay Herdr-gated, since they're no-ops there anyway). Claude/Codex keep the installer-reported state accurate and stay managed by `notify-rich`. When touching either side of this split, update both together and re-run `tests/test_herdr_plugin_notify.py` and `tests/test_gemini_herdr_notification.py`.

Non-AI shell state icons (input-wait ✋ from `_start_prompt_wait_notification`/`_finish_prompt_wait_notification` in `shell/zsh/alias/utils.zsh`, and long-command completion ✅/failure ❌ from the `shell/zsh/notification.zsh` precmd/preexec hooks) mirror to Herdr the same way tmux gets them: `notify --tmux-icon` (`shell/zsh/alias/notification.zsh`) now also calls `shell/tmux/herdr_status_icon.sh`'s `update_herdr_status_icon`/`remove_herdr_status_icon` whenever `TMUX` is unset and `HERDR_ENV`/`HERDR_PANE_ID` is set (tmux and Herdr are mutually exclusive, so both call sites are safe to run unconditionally). A normal (non-popup) Herdr pane exposes `HERDR_PANE_ID`/`HERDR_TAB_ID`/`HERDR_WORKSPACE_ID` directly as env vars — no `herdr pane get` round-trip needed, unlike the popup-only `HERDR_ACTIVE_PANE_ID` case documented elsewhere in this file. Tab labels are updated last-write-wins (mirroring tmux window names); the AI identifier prefix (✴️/💎/🪷) already on a label is preserved and only the status glyph is swapped, via `tmux_window_name.py`'s `compute-updated-label`/`compute-cleaned-label` CLI subcommands — pure functions that compute a label string without touching tmux or `herdr`, so Herdr's shell script can reuse the exact same prefix logic as the tmux hooks. Workspace-level aggregation (Herdr's "spaces" sidebar) mirrors tmux's session-level `@session_ai_status` OR-aggregation (`shell/tmux/update-session-ai-status.sh`, priority ✋>❌>🤖>✅) via `herdr workspace report-metadata <id> --source shell-status --token shell_status=<emoji>`; the sidebar surfaces it through the `$shell_status` token column in `terminal/herdr/config.toml`'s `[ui.sidebar.spaces] rows` (requires `herdr server reload-config` to pick up — this config file is not live-reloaded like the symlinked shell scripts).

## AI Prompt File Editing

When editing AI prompt files in this repository:

- **Default to English** for new or modified content (reduces token consumption); if the original file uses a different language, follow it (e.g. Japanese character dialogue examples)
- **Write concisely**: as concise as meaning and intent allow — every loaded prompt consumes context. When condensing existing files, follow `ai/common/prompt_shortening_guide.md`.
- **Runtime loading differs per platform**: Claude Code and Gemini CLI load only the markdown body of agent/skill files as the prompt — frontmatter (including YAML `#` comments) costs zero runtime tokens. Codex instead injects the whole SKILL.md raw at invocation, so every Codex skill frontmatter line counts as prompt cost. Codex agent TOML files are parsed; `#` comments there cost nothing.
- **GENERATED-file notices** are placed where they cost no runtime tokens: YAML frontmatter comments for Claude/Gemini `pr-reviewer-*.md`, a `#` comment for Codex `pr_reviewer_*.toml`. Codex `SKILL.md` files intentionally carry no notice (raw injection would bill it) — the adjacent `skill_head.md` sources and this file are the edit guard. Do not add visible-body notices to generated files.
- **Verify regeneration before committing generated outputs**: for shared-core skills, use `verify_ai_skill_generation_idempotency` from the regeneration table; it generates twice and fails if any SHA-256 changes. For other generators, after updating sources and running the generator once, record each generated output's hash, re-run the generator, and confirm the hash is unchanged. The output may legitimately differ from `HEAD`; review that diff separately. A changed hash on the second run means the first output was stale or generation is not idempotent.

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
