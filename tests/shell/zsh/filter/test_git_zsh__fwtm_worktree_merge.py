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
class FwtmTest(unittest.TestCase):
    """fwtm only selects a target branch and delegates to wtm."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.filter_input = self.root / "filter-input"
        self.wtm_calls = self.root / "wtm-calls"
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
            "[ \"${FWTM_WTL_STATUS:-0}\" -ne 0 ] && exit \"$FWTM_WTL_STATUS\"\n"
            "printf '%s' \"$FWTM_LIST_JSON\"\n",
        )
        self._write_executable(
            "filter",
            "#!/bin/sh\n"
            "cat > \"$FWTM_FILTER_INPUT\"\n"
            "[ \"${FWTM_FILTER_CANCEL:-}\" = 1 ] && exit 0\n"
            "grep \"^$FWTM_FILTER_BRANCH\" \"$FWTM_FILTER_INPUT\" | head -1\n",
        )
        self._write_executable(
            "wtm",
            "#!/bin/sh\n"
            "printf '%s\\n' \"$*\" >> \"$FWTM_WTM_CALLS\"\n"
            "exit \"${FWTM_WTM_STATUS:-0}\"\n",
        )

    def list_json(self, schema):
        items = [
            {
                "kind": "worktree",
                "branch": "main",
                "path": "/tmp/repository",
                "is_current": False,
            },
            {
                "kind": "worktree",
                "branch": "feature/login",
                "path": "/tmp/feature",
                "is_current": True,
            },
            {
                "kind": "worktree",
                "branch": None,
                "path": "/tmp/detached",
                "is_current": False,
            },
        ]
        if schema == 1:
            return json.dumps(items)
        return json.dumps(
            {
                "schema": 2,
                "items": [
                    {
                        "branch": item["branch"],
                        "worktree": {
                            "path": item["path"],
                            "current": item["is_current"],
                            "detached": item["branch"] is None,
                        },
                    }
                    for item in items
                ],
            }
        )

    def run_fwtm(self, schema=1, *, extra_env=None):
        env = {
            **os.environ,
            "PATH": f"{self.bin_dir}:{os.environ['PATH']}",
            "EXIT_CODE_SIGINT": "130",
            "FWTM_LIST_JSON": self.list_json(schema),
            "FWTM_FILTER_INPUT": str(self.filter_input),
            "FWTM_FILTER_BRANCH": "main",
            "FWTM_WTM_CALLS": str(self.wtm_calls),
            **(extra_env or {}),
        }
        result = subprocess.run(
            [
                ZSH,
                "-fc",
                f'source "{GIT_FILTER}"; fwtm; print -r -- "__STATUS=$?"',
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

    def assert_delegates_once(self, schema):
        result, status = self.run_fwtm(schema=schema)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(status, "0", result.stderr)
        self.assertEqual(
            self.filter_input.read_text(encoding="utf-8").splitlines(),
            ["main\t/tmp/repository"],
        )
        self.assertEqual(
            self.wtm_calls.read_text(encoding="utf-8").splitlines(), ["main"]
        )

    def test_schema_1_selection_delegates_to_wtm_once(self):
        self.assert_delegates_once(schema=1)

    def test_schema_2_selection_delegates_to_wtm_once(self):
        self.assert_delegates_once(schema=2)

    def test_propagates_wtm_failure_status(self):
        result, status = self.run_fwtm(extra_env={"FWTM_WTM_STATUS": "17"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(status, "17", result.stderr)
        self.assertEqual(
            self.wtm_calls.read_text(encoding="utf-8").splitlines(), ["main"]
        )

    def test_returns_sigint_without_delegating_when_selection_is_cancelled(self):
        result, status = self.run_fwtm(extra_env={"FWTM_FILTER_CANCEL": "1"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(status, "130", result.stderr)
        self.assertFalse(self.wtm_calls.exists())

    def test_returns_sigint_without_delegating_when_no_candidate_exists(self):
        current_only = json.dumps(
            [
                {
                    "kind": "worktree",
                    "branch": "feature/login",
                    "path": "/tmp/feature",
                    "is_current": True,
                },
                {
                    "kind": "worktree",
                    "branch": None,
                    "path": "/tmp/detached",
                    "is_current": False,
                },
            ]
        )
        result, status = self.run_fwtm(
            extra_env={"FWTM_LIST_JSON": current_only}
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(status, "130", result.stderr)
        self.assertIn("統合可能なworktreeがありません", result.stderr)
        self.assertFalse(self.filter_input.exists())
        self.assertFalse(self.wtm_calls.exists())

    def test_preserves_wtl_failure_without_opening_picker_or_delegating(self):
        result, status = self.run_fwtm(extra_env={"FWTM_WTL_STATUS": "23"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(status, "23", result.stderr)
        self.assertFalse(self.filter_input.exists())
        self.assertFalse(self.wtm_calls.exists())


if __name__ == "__main__":
    unittest.main()
