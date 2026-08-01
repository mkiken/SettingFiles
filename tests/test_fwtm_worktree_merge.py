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


class FwtmTest(unittest.TestCase):
    """fwtm: Worktrunk JSONから統合先branchを選択し、現在worktreeでwt mergeする"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.current = self.root / "current"
        self.feature = self.root / "feature"
        self.detached = self.root / "detached"
        for path in (self.current, self.feature, self.detached):
            path.mkdir()
        self.filter_input = self.root / "filter-input"
        self.merge_log = self.root / "merge-log"
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
            "wt",
            "#!/bin/sh\n"
            "printf '%s\\n' \"$PWD|$*\" >> \"$FWTM_MERGE_LOG\"\n"
            "exit \"${FWTM_MERGE_STATUS:-0}\"\n",
        )

    def list_json(self, schema):
        items = [
            {
                "kind": "worktree",
                "branch": "main",
                "path": str(self.current),
                "is_current": True,
            },
            {
                "kind": "worktree",
                "branch": "feature/login",
                "path": str(self.feature),
                "is_current": False,
            },
            {
                "kind": "worktree",
                "branch": None,
                "path": str(self.detached),
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

    def run_fwtm(self, schema=1, extra_env=None):
        env = {
            **os.environ,
            "PATH": f"{self.bin_dir}:{os.environ['PATH']}",
            "EXIT_CODE_SIGINT": "130",
            "FWTM_LIST_JSON": self.list_json(schema),
            "FWTM_FILTER_INPUT": str(self.filter_input),
            "FWTM_FILTER_BRANCH": "feature/login",
            "FWTM_MERGE_LOG": str(self.merge_log),
            **(extra_env or {}),
        }
        script = f'''
            source "{GIT_FILTER}"
            fwtm
            exit_code=$?
            print -r -- "__STATUS=$exit_code"
        '''
        result = subprocess.run(
            [ZSH, "-fc", script],
            cwd=self.current,
            capture_output=True,
            text=True,
            env=env,
        )
        values = {
            line.split("=", 1)[0]: line.split("=", 1)[1]
            for line in result.stdout.splitlines()
            if line.startswith("__")
        }
        return result, values

    def test_extracts_schema_1_and_merges_current_worktree_to_selected_branch(self):
        result, values = self.run_fwtm(schema=1)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "0", result.stderr)
        self.assertEqual(
            self.filter_input.read_text().splitlines(),
            [f"feature/login\t{self.feature}"],
        )
        self.assertEqual(self.merge_log.read_text().splitlines(), [f"{self.current.resolve()}|merge feature/login"])

    def test_extracts_schema_2_and_merges_current_worktree_to_selected_branch(self):
        result, values = self.run_fwtm(schema=2)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "0", result.stderr)
        self.assertEqual(
            self.filter_input.read_text().splitlines(),
            [f"feature/login\t{self.feature}"],
        )
        self.assertEqual(self.merge_log.read_text().splitlines(), [f"{self.current.resolve()}|merge feature/login"])

    def test_returns_sigint_when_selection_is_cancelled(self):
        result, values = self.run_fwtm(extra_env={"FWTM_FILTER_CANCEL": "1"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "130", result.stderr)
        self.assertFalse(self.merge_log.exists())

    def test_returns_sigint_when_no_merge_candidate_exists(self):
        current_only = json.dumps(
            [
                {
                    "kind": "worktree",
                    "branch": "main",
                    "path": str(self.current),
                    "is_current": True,
                },
                {
                    "kind": "worktree",
                    "branch": None,
                    "path": str(self.detached),
                    "is_current": False,
                },
            ]
        )
        result, values = self.run_fwtm(extra_env={"FWTM_LIST_JSON": current_only})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "130", result.stderr)
        self.assertIn("統合可能なworktreeがありません", result.stderr)
        self.assertFalse(self.merge_log.exists())

    def test_preserves_wt_merge_exit_status(self):
        result, values = self.run_fwtm(extra_env={"FWTM_MERGE_STATUS": "42"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "42", result.stderr)
        self.assertEqual(self.merge_log.read_text().splitlines(), [f"{self.current.resolve()}|merge feature/login"])

    def test_preserves_wtl_failure_status_without_opening_the_picker(self):
        result, values = self.run_fwtm(extra_env={"FWTM_WTL_STATUS": "23"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "23", result.stderr)
        self.assertFalse(self.filter_input.exists())
        self.assertFalse(self.merge_log.exists())


if __name__ == "__main__":
    unittest.main()
