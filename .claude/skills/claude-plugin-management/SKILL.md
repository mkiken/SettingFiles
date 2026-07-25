---
name: claude-plugin-management
description: Use when adding, updating, or removing a Claude Code plugin in this repository — mac/scripts/ai/claude.sh setup functions, ai/claude/settings.json enabledPlugins/extraKnownMarketplaces, or the mac/initialization/ai/claude.sh and mac/updates/claude.sh call sites and their tests.
---

# Claude Plugin Management

Adding a Claude Code plugin to this repository touches four files plus tests, in a fixed pattern. Skipping any one of them is exactly how `tsumiki` and `dev-browser` ended up half-wired (installed only on first `mac/initialize`, never reconciled by `mac/update`).

## Marketplace name vs. repo slug

A marketplace's registered `name` (from its `.claude-plugin/marketplace.json`) is **not always** the same as its GitHub repo slug. `context-mode` and `tsumiki` happen to coincide; `thedotmack` (repo `thedotmack/claude-mem`) and `kuu-marketplace` (repo `fumiya-kume/claude-code`) do not. Before wiring a new plugin, fetch the target repo's `.claude-plugin/marketplace.json` and read its `name` field — do not assume the repo basename. See "External Identifiers" in the root `CLAUDE.md` for the broader rule this instance follows.

Three different identifiers are used across one setup function, and mixing them up is the single most common mistake:

| Operation | Identifier to use | Why |
| --- | --- | --- |
| `claude plugin marketplace add` | repo slug (`owner/repo`) | Claude doesn't know the marketplace name until it fetches `marketplace.json` |
| `claude plugin marketplace update` / the `grep` guard before `add` | marketplace **name** | Registered marketplaces are looked up by name, not repo |
| `claude plugin {list,install,update,enable}` | `<plugin>@<marketplace-name>` | Plugin IDs are always `plugin@marketplace-name` |

## The four files (plus tests)

Reference implementation: `setup_claude_superpowers` in `mac/scripts/ai/claude.sh`. Copy its structure exactly (marketplace-exists guard → `marketplace update` → install-or-update branch on `plugin list --json` → enable-if-not-enabled check, each step `|| return 1`).

1. **`mac/scripts/ai/claude.sh`** — add `setup_claude_<name>()` following the reference implementation.
2. **`ai/claude/settings.json`** — add to `enabledPlugins` (`"<plugin>@<marketplace>": true`) and `extraKnownMarketplaces` (name-keyed, `{"source": {"repo": "...", "source": "github"}}` for a GitHub repo add, or `{"source": {"source": "git", "url": "..."}}` for a bare git URL like `tsumiki`). Keep both objects alphabetically sorted by key — this is a hand-maintained convention with no enforcing test, so check it manually (`python3 -c "import json; ..."` sorted-keys check).
3. **`mac/initialization/ai/claude.sh`** — call the new setup function. Must stay above the `setup_gsd_core_for_runtime` line (see `tests/test_gsd_core_setup.py`'s ordering assertion).
4. **`mac/updates/claude.sh`** — call the new setup function in the **same relative position**. This is the step tsumiki/dev-browser skipped; omitting it means the plugin never gets installed/repaired on existing machines, only on fresh `mac/initialize` runs.
5. **`tests/test_context_mode_setup.py`** — despite its name, this file is the de-facto test suite for all Claude/Gemini/Codex plugin wiring (it already covers claude-mem, context-mode, superpowers). Extend it rather than creating a new file:
   - Add the new function name to the `mac/scripts/ai/claude.sh` tuple in `test_assistant_specific_setup_functions_are_defined_in_own_files`.
   - Add the new function name to **both** the init and update tuples in `test_ai_setup_and_update_scripts_source_assistant_setup_before_calls` — this single addition is what structurally prevents the tsumiki/dev-browser drift, because the test's `assert_source_before_call` raises if the call string is absent from either script.
   - Add a settings-registration test mirroring `test_claude_settings_register_claude_mem_plugin`.
   - If the marketplace name differs from the repo slug, add an explicit test with `assertIn`/`assertNotIn` pairs asserting the correct identifier is used in each of the three roles above — this catches a future contributor copy-pasting a wrong ID from an external article.

## `smart_merge_json` never propagates deletions

`ai/claude/settings.json` is merged into the live `~/.claude/settings.json` via `smart_merge_json` (additive, key-wise recursive union — see `jq_deepmerge` in `shell/zsh/alias/utils.zsh`). Editing the repo file alone changes nothing live until `mac/initialization/ai/claude.sh` or `mac/updates/claude.sh` runs, and **removing** an entry from the repo file does not remove it live. To fully remove a plugin:

1. Delete its `enabledPlugins`/`extraKnownMarketplaces` entries from `ai/claude/settings.json` and its setup-function call sites from both init and update scripts.
2. On the live machine: `claude plugin uninstall <plugin>@<marketplace>` then `claude plugin marketplace remove <marketplace>` — these clean up `~/.claude/settings.json` automatically, so no manual JSON editing is normally needed.
3. Verify with `claude plugin list --json | jq '.[] | select(.id|test("<plugin>"))'` (expect empty) and `grep -c <plugin> ~/.claude/settings.json` (expect 0 or no match).

A leftover `.orphaned_at`-marked directory under `~/.claude/plugins/cache/<marketplace>/` after uninstall is Claude Code's own GC bookkeeping, not a stray artifact of this repo's tooling — leave it for Claude Code to reap rather than deleting it by hand.
