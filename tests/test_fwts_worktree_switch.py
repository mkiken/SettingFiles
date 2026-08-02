import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GIT_FILTER = REPO_ROOT / "shell/zsh/filter/git.zsh"
ZSH = shutil.which("zsh")


@unittest.skipUnless(ZSH, "zsh is required")
class FwtsTest(unittest.TestCase):
    """fwts: filter選択branchをworktrunk switchへ渡す。"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.filter_input = self.root / "filter-input"
        self.switch_args = self.root / "switch-args"
        self._write_fake_commands()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_executable(self, name: str, body: str):
        path = self.bin_dir / name
        path.write_text(body)
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def _write_fake_commands(self):
        self._write_executable(
            "wtl",
            "#!/bin/sh\n"
            "printf '%s' \"$FWTS_LIST_JSON\"\n",
        )
        self._write_executable(
            "filter",
            "#!/bin/sh\n"
            "cat > \"$FWTS_FILTER_INPUT\"\n"
            "[ \"${FWTS_FILTER_CANCEL:-}\" = 1 ] && exit 0\n"
            "grep \"^$FWTS_FILTER_BRANCH\" \"$FWTS_FILTER_INPUT\" | head -1\n",
        )
        self._write_executable(
            "wts",
            "#!/bin/sh\n"
            "printf '%s\\n' \"$@\" > \"$FWTS_SWITCH_ARGS\"\n",
        )

    def run_fwts(self, schema=1, *, extra_env=None):
        items = [
            {"kind": "worktree", "branch": "main", "path": "/tmp/main"},
            {"kind": "worktree", "branch": "feature/login", "path": "/tmp/login"},
            {"kind": "worktree", "branch": None, "path": "/tmp/detached"},
        ]
        list_json = (
            json.dumps(items)
            if schema == 1
            else json.dumps(
                {
                    "schema": 2,
                    "items": [
                        {
                            "branch": item["branch"],
                            "worktree": {"path": item["path"]},
                        }
                        for item in items
                    ],
                }
            )
        )
        env = {
            **os.environ,
            "PATH": f"{self.bin_dir}:{os.environ['PATH']}",
            "EXIT_CODE_SIGINT": "130",
            "FWTS_LIST_JSON": list_json,
            "FWTS_FILTER_INPUT": str(self.filter_input),
            "FWTS_FILTER_BRANCH": "feature/login",
            "FWTS_SWITCH_ARGS": str(self.switch_args),
            **(extra_env or {}),
        }
        result = subprocess.run(
            [ZSH, "-fc", f'source "{GIT_FILTER}"; fwts; print -r -- "__STATUS=$?"'],
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

    def test_switches_selected_schema_1_worktree(self):
        result, status = self.run_fwts()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(status, "0", result.stderr)
        self.assertEqual(self.filter_input.read_text().splitlines(), ["main\t/tmp/main", "feature/login\t/tmp/login"])
        self.assertEqual(self.switch_args.read_text(), "feature/login\n")

    def test_switches_selected_schema_2_worktree(self):
        result, status = self.run_fwts(schema=2)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(status, "0", result.stderr)
        self.assertEqual(self.switch_args.read_text(), "feature/login\n")

    def test_returns_sigint_without_switch_when_selection_is_cancelled(self):
        result, status = self.run_fwts(extra_env={"FWTS_FILTER_CANCEL": "1"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(status, "130", result.stderr)
        self.assertFalse(self.switch_args.exists())
