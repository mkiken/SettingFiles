---
name: herdr-dev
description: Use when developing or configuring Herdr integration in this repository — terminal/herdr/config.toml keybindings, [[keys.command]] popups, mac/scripts/herdr.sh installer flow, Herdr plugins (notify-rich), Gemini's Herdr notification split, or shell status icon mirroring (shell/tmux/herdr_status_icon.sh). Not for merely operating the herdr CLI from inside a pane (that is the separate herdr skill).
---

# Herdr Integration Development

Domain knowledge for changing this repository's Herdr configuration and integrations. For *operating* the `herdr` CLI from inside a Herdr-managed pane, use the vendored `ai/common/skills/herdr` skill instead — it is synced from upstream and must not be extended with repo knowledge.

Detail lives in `references/` next to this file. Read the matching reference file IN FULL with your file-reading tool BEFORE editing any file it covers — this router only routes and is not sufficient to make a change safely. Paths below are relative to this skill directory (`.claude/skills/herdr-dev/` from the repository root; the same directory is also reachable as `.agents/skills/herdr-dev/`).

## Routing

| Task | Read |
| --- | --- |
| Keybindings in `terminal/herdr/config.toml` | `references/keybindings.md` |
| `[[keys.command]]` popups, sending text to panes, new-pane startup races | `references/popups.md` + `references/plugin-env.md` |
| `mac/scripts/herdr.sh` installer flow, `herdr integration install`, `sync_herdr_skill` | `references/installer.md` |
| Herdr plugins / notify-rich: `[[events]]` hookability, notification gating, tab labels, Gemini's opt-out, codex summary bodies | `references/notify-rich.md` + `references/plugin-env.md` |
| Shell status icon mirroring (`shell/tmux/herdr_status_icon.sh`), workspace aggregation, sticky ✋ | `references/status-icon.md` |
| Anything running as a child of the herdr server (popup command, `[[events]]` hook) | `references/plugin-env.md` |

## Always true

Never run `herdr integration install` against live Claude or Codex configuration — always use the repository helper (`mac/scripts/herdr.sh`).

Some changes span two sides and must be edited and tested together: the Gemini split (`notify-on-agent-status.sh` + `ai/gemini/hooks/notification.sh` → `tests/test_herdr_plugin_notify.py` + `tests/test_gemini_herdr_notification.py`), and tab labels (the plugin's label rebuild + the shell icon functions → `tests/test_herdr_plugin_notify.py` + `tests/test_herdr_status_icon.py`). Each reference file names its own required tests.
