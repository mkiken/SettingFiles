import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT

GIT_FILTER = REPO_ROOT / "shell/zsh/filter/git.zsh"
ZSH = shutil.which("zsh")


@unittest.skipUnless(ZSH, "zsh is required")
class FwtrTest(unittest.TestCase):
    """fwtr selects removable worktrees and delegates once to wtr."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.filter_input = self.root / "filter-input"
        self.filter_args = self.root / "filter-args"
        self.wtr_args = self.root / "wtr-args"
        self.wtl_args = self.root / "wtl-args"
        self._write_fake_commands()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_executable(self, name: str, body: str):
        path = self.bin_dir / name
        path.write_text(body, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def _write_fake_commands(self):
        self._write_executable(
            "wtl",
            "#!/bin/sh\n"
            "printf '%s\\n' \"$@\" > \"$FWTR_WTL_ARGS\"\n"
            "[ \"${FWTR_WTL_STATUS:-0}\" -ne 0 ] && exit \"$FWTR_WTL_STATUS\"\n"
            "printf '%s' \"$FWTR_LIST_JSON\"\n",
        )
        self._write_executable(
            "filter",
            "#!/bin/sh\n"
            "printf '%s\\n' \"$@\" > \"$FWTR_FILTER_ARGS\"\n"
            "cat > \"$FWTR_FILTER_INPUT\"\n"
            "[ \"${FWTR_FILTER_CANCEL:-}\" = 1 ] && exit 0\n"
            "printf '%s\\n' \"$FWTR_FILTER_SELECTION\"\n",
        )
        self._write_executable(
            "wtr",
            "#!/bin/sh\n"
            "printf '%s\\n' \"$@\" > \"$FWTR_WTR_ARGS\"\n"
            "exit \"${FWTR_WTR_STATUS:-0}\"\n",
        )

    def list_json(self):
        return json.dumps(
            {
                "schema": 2,
                "items": [
                    {
                        "branch": "main",
                        "worktree": {"path": "/tmp/main", "current": False},
                    },
                    {
                        "branch": "feature/old",
                        "worktree": {"path": "/tmp/old", "current": False},
                    },
                    {
                        "branch": "feature/current",
                        "worktree": {"path": "/tmp/current", "current": True},
                    },
                    {
                        "branch": None,
                        "worktree": {"path": "/tmp/detached", "current": False},
                    },
                ],
            }
        )

    def run_fwtr(self, *, extra_env=None):
        env = {
            **os.environ,
            "PATH": f"{self.bin_dir}:{os.environ['PATH']}",
            "EXIT_CODE_SIGINT": "130",
            "FWTR_LIST_JSON": self.list_json(),
            "FWTR_FILTER_INPUT": str(self.filter_input),
            "FWTR_FILTER_ARGS": str(self.filter_args),
            "FWTR_FILTER_SELECTION": "main\t/tmp/main\nfeature/old\t/tmp/old",
            "FWTR_WTR_ARGS": str(self.wtr_args),
            "FWTR_WTL_ARGS": str(self.wtl_args),
            **(extra_env or {}),
        }
        result = subprocess.run(
            [
                ZSH,
                "-fc",
                f'source "{GIT_FILTER}"; fwtr; print -r -- "__STATUS=$?"',
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            env=env,
        )
        status = next(
            line.split("=", 1)[1]
            for line in result.stdout.splitlines()
            if line.startswith("__STATUS=")
        )
        return result, status

    def test_multi_selection_delegates_once_with_selected_branches(self):
        result, status = self.run_fwtr()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(status, "0", result.stderr)
        self.assertEqual(
            self.filter_input.read_text(encoding="utf-8").splitlines(),
            ["main\t/tmp/main", "feature/old\t/tmp/old"],
        )
        self.assertEqual(
            self.wtr_args.read_text(encoding="utf-8").splitlines(),
            ["main", "feature/old"],
        )
        self.assertEqual(
            self.wtl_args.read_text(encoding="utf-8").splitlines(),
            ["--format=json", "--config-set", "list.json-schema=2"],
        )
        self.assertIn("--multi", self.filter_args.read_text(encoding="utf-8"))

    def test_propagates_wtr_failure_status(self):
        result, status = self.run_fwtr(extra_env={"FWTR_WTR_STATUS": "17"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(status, "17", result.stderr)

    def test_returns_sigint_without_delegating_when_selection_is_cancelled(self):
        result, status = self.run_fwtr(extra_env={"FWTR_FILTER_CANCEL": "1"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(status, "130", result.stderr)
        self.assertFalse(self.wtr_args.exists())

    def test_returns_sigint_without_delegating_when_no_candidate_exists(self):
        current_only = json.dumps(
            {
                "schema": 2,
                "items": [
                    {
                        "branch": "feature/current",
                        "worktree": {"path": "/tmp/current", "current": True},
                    },
                    {
                        "branch": None,
                        "worktree": {"path": "/tmp/detached", "current": False},
                    },
                ],
            }
        )
        result, status = self.run_fwtr(extra_env={"FWTR_LIST_JSON": current_only})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(status, "130", result.stderr)
        self.assertFalse(self.wtr_args.exists())

    def test_returns_sigint_without_delegating_for_malformed_selection(self):
        result, status = self.run_fwtr(
            extra_env={"FWTR_FILTER_SELECTION": "feature/old"}
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(status, "130", result.stderr)
        self.assertFalse(self.wtr_args.exists())

    def test_propagates_wtl_failure_status(self):
        result, status = self.run_fwtr(extra_env={"FWTR_WTL_STATUS": "19"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(status, "19", result.stderr)
        self.assertFalse(self.wtr_args.exists())
