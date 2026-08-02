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
class FwtsTest(unittest.TestCase):
    """fwts: filter選択branchをworktrunk switchへ渡す。"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.filter_input = self.root / "filter-input"
        self.switch_args = self.root / "switch-args"
        self.wtl_args = self.root / "wtl-args"
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
            "printf '%s\\n' \"$@\" > \"$FWTS_WTL_ARGS\"\n"
            "[ \"${FWTS_WTL_STATUS:-0}\" -ne 0 ] && exit \"$FWTS_WTL_STATUS\"\n"
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

    def run_fwts(self, *, extra_env=None):
        list_json = json.dumps(
            {
                "schema": 2,
                "items": [
                    {
                        "branch": "main",
                        "display": {"symbols": "^"},
                        "worktree": {"path": "/tmp/main", "changes": {"diff": {"added": 0, "deleted": 0}}},
                        "head": {"short_sha": "main1234", "committed_at": "2026-08-01T00:00:00Z", "subject": "Main commit"},
                    },
                    {
                        "branch": "feature/login",
                        "display": {"symbols": "!?↑"},
                        "worktree": {"path": "/tmp/login", "changes": {"diff": {"added": 12, "deleted": 3}}},
                        "default_branch": {"ahead": 2, "behind": 1, "diff": {"added": 30, "deleted": 8}},
                        "upstream": {"ahead": 4, "behind": 0},
                        "head": {"short_sha": "feature1", "committed_at": "2026-08-01T00:00:00Z", "subject": "Add login page"},
                    },
                    {"branch": None, "worktree": {"path": "/tmp/detached"}},
                ],
            }
        )
        env = {
            **os.environ,
            "PATH": f"{self.bin_dir}:{os.environ['PATH']}",
            "EXIT_CODE_SIGINT": "130",
            "FWTS_LIST_JSON": list_json,
            "FWTS_FILTER_INPUT": str(self.filter_input),
            "FWTS_FILTER_BRANCH": "feature/login",
            "FWTS_SWITCH_ARGS": str(self.switch_args),
            "FWTS_WTL_ARGS": str(self.wtl_args),
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

    def test_formats_schema_2_worktree_and_switches_selected_branch(self):
        result, status = self.run_fwts()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(status, "0", result.stderr)
        candidates = self.filter_input.read_text().splitlines()
        main = candidates[0].split("\t")
        self.assertEqual(main[:8], ["main", "^", "", "", "", "", "/tmp/main", "main1234"])
        self.assertRegex(main[8], r"^\d+(?:s|m|h|d|w|mo|y)$")
        self.assertEqual(main[9], "Main commit")
        feature = candidates[1].split("\t")
        self.assertEqual(feature[:8], ["feature/login", "!?↑", "+12 -3", "↑2 ↓1", "+30 -8", "↑4", "/tmp/login", "feature1"])
        self.assertRegex(feature[8], r"^\d+(?:s|m|h|d|w|mo|y)$")
        self.assertEqual(feature[9], "Add login page")
        self.assertEqual(
            self.wtl_args.read_text().splitlines(),
            ["--format=json", "--config-set", "list.json-schema=2"],
        )
        self.assertEqual(self.switch_args.read_text(), "feature/login\n")

    def test_returns_sigint_without_switch_when_selection_is_cancelled(self):
        result, status = self.run_fwts(extra_env={"FWTS_FILTER_CANCEL": "1"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(status, "130", result.stderr)
        self.assertFalse(self.switch_args.exists())

    def test_preserves_wtl_failure_without_opening_picker_or_switching(self):
        result, status = self.run_fwts(extra_env={"FWTS_WTL_STATUS": "23"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(status, "23", result.stderr)
        self.assertFalse(self.filter_input.exists())
        self.assertFalse(self.switch_args.exists())
