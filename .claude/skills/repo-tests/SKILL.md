---
name: repo-tests
description: Use when adding, moving, or restructuring tests in this repository — a new test file or directory under tests/, test ownership and naming, tests/dependencies.toml entries, shell-function tests for shell/{tmux,herdr}, or a test that pins an exclusion. Not needed merely to run the suite (CLAUDE.md covers that).
---

# Repository Test Authoring

`CLAUDE.md` ("Run Tests") holds the always-on rules: run tests for every change, update pinned expectations, targeted vs. full-suite selection, the move/rename grep trap, sharding, and `sanitized_env()`. This skill holds the authoring conventions.

## Ownership and naming

Main-suite tests mirror their primary implementation owner: `tests/<normalized source parent>/test_<source name>[__scenario].py`. Python source names omit `.py`; other extensions remain encoded in the test name. A test that exercises several files stays with the entrypoint or canonical source that owns its behavior; do not add ordinary ownership to a map.

## New test directories

A new test directory needs an `__init__.py`. The runner rejects uncollected files; confirm the expected test count after adding the first file in a directory.

## `tests/dependencies.toml`

Record exceptional dependencies supported by an observed wider-run failure or by inspecting the implementation and test. Pin selection with a test and verify `--paths <source>` selects it. Use `[untested]` only for an exact path with a nonempty reason when no executable test applies. Unmapped paths stop the runner.

## Shell-function tests

`tests/shell/{tmux,herdr}/test_<name>_sh.py` tests shell functions by sourcing the `.sh`, invoking functions via `bash -c`, and asserting stdout/status; follow `tests/shell/tmux/test_ai_notification_summary_sh.py`'s `run_fn` pattern. Use this style so `unittest discover` collects new shell-function tests; standalone `.sh` tests are ignored.

## Pinned exclusions

When a test pins an exclusion (e.g. `assertNotIn`, a must-not-subscribe list), state the reason in an adjacent comment — an unexplained negative pin forces a later session to rediscover the rejection through history archaeology, or to re-attempt the rejected approach.
