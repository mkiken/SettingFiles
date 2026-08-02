"""Herdr lazygit popupのtask worktree contextテスト。"""
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT

CONTEXT_SCRIPT = REPO_ROOT / "shell/tmux/herdr_worktree_context.sh"
LAUNCHER_SCRIPT = REPO_ROOT / "shell/tmux/herdr-open-lazygit.sh"


def context_relpath(tab_id: str, socket_path: str = "default") -> Path:
    sanitize = lambda value: re.sub(r"[^A-Za-z0-9._-]", "_", value)
    return Path("herdr-task-worktree") / sanitize(socket_path) / sanitize(tab_id)


class HerdrLazygitContextTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.fake_bin = self.root / "bin"
        self.fake_bin.mkdir()
        self.cache_dir = self.root / "cache"
        self.trash_dir = self.root / "trash"
        self.lazygit_log = self.root / "lazygit.log"
        self._write_fake("herdr", '''#!/bin/bash
printf '{"result":{"pane":{"tab_id":"%s"}}}\n' "$HERDR_TEST_TAB_ID"
''')
        self._write_fake("lazygit", '''#!/bin/bash
printf '%s\\n%s\\n' "$PWD" "$XDG_CONFIG_HOME" > "$HERDR_TEST_LAZYGIT_LOG"
''')
        self._write_fake("trash", '''#!/bin/bash
mkdir -p "$HERDR_TEST_TRASH_DIR"
mv "$1" "$HERDR_TEST_TRASH_DIR/$(basename "$1")"
''')

        self.source_dir = self.root / "source"
        self.source_dir.mkdir()
        self.task_dir = self.root / "task"
        subprocess.run(["git", "init", "-q", str(self.task_dir)], check=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_fake(self, name: str, content: str):
        path = self.fake_bin / name
        path.write_text(content, encoding="utf-8")
        path.chmod(0o755)

    def _env(self, **extra):
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{self.fake_bin}{os.pathsep}{env['PATH']}",
                "HERDR_BIN_PATH": str(self.fake_bin / "herdr"),
                "HERDR_TEST_TAB_ID": "tab:1",
                "HERDR_TEST_LAZYGIT_LOG": str(self.lazygit_log),
                "HERDR_TEST_TRASH_DIR": str(self.trash_dir),
                "HERDR_SOCKET_PATH": "default",
                "XDG_CACHE_HOME": str(self.cache_dir),
            }
        )
        env.update(extra)
        return env

    def _set_context(self):
        subprocess.run(
            [
                "bash",
                "-c",
                'source "$1" && set_herdr_task_worktree_context "$2"',
                "bash",
                str(CONTEXT_SCRIPT),
                str(self.task_dir),
            ],
            check=True,
            env=self._env(HERDR_ENV="1", HERDR_TAB_ID="tab:1"),
        )

    def test_launcher_prefers_recorded_task_worktree(self):
        self._set_context()

        subprocess.run(
            ["bash", str(LAUNCHER_SCRIPT)],
            check=True,
            env=self._env(HERDR_ACTIVE_PANE_ID="pane:1", HERDR_ACTIVE_PANE_CWD=str(self.source_dir)),
        )

        self.assertEqual(
            self.lazygit_log.read_text(encoding="utf-8").splitlines(),
            [str(self.task_dir), str(Path.home() / ".config")],
        )

    def test_launcher_uses_active_pane_cwd_without_task_context(self):
        subprocess.run(
            ["bash", str(LAUNCHER_SCRIPT)],
            check=True,
            env=self._env(HERDR_ACTIVE_PANE_ID="pane:1", HERDR_ACTIVE_PANE_CWD=str(self.source_dir)),
        )

        self.assertEqual(
            self.lazygit_log.read_text(encoding="utf-8").splitlines()[0],
            str(self.source_dir),
        )

    def test_stale_context_is_cleared_before_active_pane_fallback(self):
        state_file = self.cache_dir / context_relpath("tab:1")
        state_file.parent.mkdir(parents=True)
        state_file.write_text(str(self.root / "deleted-worktree") + "\n", encoding="utf-8")

        subprocess.run(
            ["bash", str(LAUNCHER_SCRIPT)],
            check=True,
            env=self._env(HERDR_ACTIVE_PANE_ID="pane:1", HERDR_ACTIVE_PANE_CWD=str(self.source_dir)),
        )

        # Deleted task worktree must not route later popups to stale state.
        self.assertFalse(state_file.exists())
        self.assertEqual(
            self.lazygit_log.read_text(encoding="utf-8").splitlines()[0],
            str(self.source_dir),
        )

    def test_missing_context_and_active_cwd_does_not_start_lazygit(self):
        result = subprocess.run(
            ["bash", str(LAUNCHER_SCRIPT)],
            capture_output=True,
            text=True,
            env=self._env(HERDR_ACTIVE_PANE_ID="pane:1"),
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("lazygit was not started", result.stderr)
        # Context failure must not launch lazygit in the server's unrelated cwd.
        self.assertFalse(self.lazygit_log.exists())

    def test_clear_removes_the_recorded_context(self):
        self._set_context()
        state_file = self.cache_dir / context_relpath("tab:1")

        subprocess.run(
            [
                "bash",
                "-c",
                'source "$1" && clear_herdr_task_worktree_context',
                "bash",
                str(CONTEXT_SCRIPT),
            ],
            check=True,
            env=self._env(HERDR_ENV="1", HERDR_TAB_ID="tab:1"),
        )

        # Cleanup must restore later popup resolution to the active pane cwd.
        self.assertFalse(state_file.exists())


if __name__ == "__main__":
    unittest.main()
