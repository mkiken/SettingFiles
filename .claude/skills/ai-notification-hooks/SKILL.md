---
name: ai-notification-hooks
description: Use when changing AI notification hooks in this repository — ai/{claude,gemini,codex}/hooks/*, shell/tmux/ai_notification_*, tmux window status icons, Mac notification delivery — or their tests. Defines the required domain tests (notification smoke test, Gemini context-alert e2e, Codex hook unittests) and hook implementation rules.
---

# AI Notification Hooks

Domain knowledge for this repository's AI notification hooks (Claude / Gemini / Codex) and their tmux/Mac notification behavior. For the Herdr side (notify-rich plugin, Gemini's Herdr opt-out, status icon mirroring), also read `.claude/skills/herdr-dev/SKILL.md`.

## Required tests

When changing the notification hooks (`ai/*/hooks/*notification*.sh`, `shell/tmux/ai_notification_*.sh`), additionally run the manual smoke test `bash tests/manual/notification_hook_smoke.sh` — it feeds representative hook events to all three hooks; by default it sends real Mac notifications and updates tmux window icons, so it is kept out of unittest discovery. Pass `--silent` (sets `NOTIFY_SILENT=1`, which overrides even `NOTIFY_FORCE`) to run the same exit-code checks without any notification or tmux icon side effects. AI agents running this smoke test should default to `--silent`; use the no-flag form only when a real-notification/tmux-icon check is explicitly needed.

The Gemini hook's context-alert e2e test lives outside the main discovery path — when changing the Gemini notification hook or `shell/tmux/gemini_context_usage.py`, also run `python3 -m unittest discover -s ai/gemini/hooks/tests`.

The Codex hook unit tests also live outside the main discovery path — when changing `ai/codex/hooks/*.py`, also run `python3 -m unittest discover -s ai/codex/hooks`.

## Hook roles (`ai/claude/hooks/`, symlinked into `~/.claude/hooks/`; Gemini/Codex follow the same split)

- `claude-hook.py` - Sets the in-progress tmux window icon (🤖) and removes icons on SessionEnd
- `stop-send-notification.sh` - Owns Notification / Stop / StopFailure events: sets the tmux icon immediately on event detection for Notification (✋) / StopFailure (❌), then sends a rich Mac notification after transcript analysis. Icons are set directly (not via `notify --tmux-icon`) so they appear before the slow summary generation. For Stop, the ✅ icon and completion notification are deferred until after transcript analysis and are skipped entirely while background work is pending (`PENDING_BACKGROUND_WORK` from `claude_transcript_analyze.py`: async agents launched but not yet notified, or an armed ScheduleWakeup) — Stop fires at every turn end, and its hook input carries no background-task fields, so the transcript is the only signal. StopFailure fires when a turn aborts on an API error or a malformed tool call (Stop does NOT fire then) — without this registration such failures are silent.

## Implementation rules

- When one hook emits both a macOS notification and tmux state for the same event, complete the tmux update synchronously before calling `notify`. Use strict error reporting so tmux failures reach the hook error log without blocking the Mac notification, and cover the ordering with isolated tests.
- Shared shell header for the three platform notification hooks (sources + `NOTIFY_FORCE` + `debug_log`): `shell/tmux/ai_notification_hook_common.sh`
- Hooks that intentionally send macOS notifications must set `NOTIFY_FORCE=1` (prefer the shared header) and test delivery with `DISABLE_NOTIFY=1`; ordinary AI-spawned commands must remain suppressed.
- Suppression precedence: `NOTIFY_SILENT` > `NOTIFY_FORCE` > `DISABLE_NOTIFY`. `NOTIFY_SILENT=1` silences both the `notify` gate (`shell/zsh/alias/notification.zsh`) and tmux icon updates (`shell/tmux/tmux_window_name.sh`), overriding even `NOTIFY_FORCE` — used by the smoke test's `--silent` flag so hook-logic verification never produces a real notification or icon change.
- Stateful hooks must define their state scope and test multiple transcripts or agents sharing one session ID so one cannot reset another's state.
- Before referencing a new hook input field, confirm it actually exists: check the official hooks schema, or capture a real event (enable the hook's `DEBUG_ENABLED` log) and inspect the payload. A guard keyed to a nonexistent field degrades silently — the `background_tasks` Stop guard shipped dead and went unnoticed for weeks.
- Hook critical paths: python3 startup costs ~45ms vs ~7ms for jq/date on this machine — add a python3 process only when it replaces many subprocess launches; otherwise fold work into an existing jq query or pure bash, and benchmark baseline vs candidate before restructuring.
- Benchmarking hooks: `/bin/bash` is 3.2 (no `EPOCHREALTIME`); time hook benchmarks with perl `Time::HiRes` or zsh.
- A hook test's `run_hook`-style helper must not pass `os.environ.copy()` straight through: pop `HERDR_ENV`/`TMUX`/`TMUX_PANE` first. Hooks early-return under these guards (e.g. `codex-stop-notification.sh`'s `HERDR_ENV` check), so a test running inside such an environment silently short-circuits the hook under test instead of exercising it — see `tests/test_herdr_setup.py`'s `run_zsh` for the reference pop pattern.
