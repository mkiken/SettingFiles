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
    """fwtm: 選択target worktreeのローカルbranchへmergeする。"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.target = self.root / "repository"
        self.source = self.root / "feature"
        self.detached = self.root / "detached"
        self.detached.mkdir()
        self.filter_input = self.root / "filter-input"
        self._initialize_repository()
        self._write_fake_commands()

    def tearDown(self):
        self.temp_dir.cleanup()

    def git(self, *args, cwd=None, check=True):
        return subprocess.run(
            ["git", *args],
            cwd=cwd or self.target,
            capture_output=True,
            text=True,
            check=check,
        )

    def _initialize_repository(self):
        self.git("init", str(self.target), cwd=self.root)
        self.git("config", "user.name", "Test User")
        self.git("config", "user.email", "test@example.com")
        (self.target / "base.txt").write_text("base\n")
        self.git("add", "base.txt")
        self.git("commit", "-m", "test: base")
        self.git("branch", "-M", "main")
        self.git("worktree", "add", "-b", "feature/login", str(self.source))
        (self.source / "feature.txt").write_text("feature\n")
        self.git("add", "feature.txt", cwd=self.source)
        self.git("commit", "-m", "test: feature", cwd=self.source)

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

    def list_json(self, schema, *, current_branch="feature/login"):
        items = [
            {
                "kind": "worktree",
                "branch": "main",
                "path": str(self.target),
                "is_current": current_branch == "main",
            },
            {
                "kind": "worktree",
                "branch": "feature/login",
                "path": str(self.source),
                "is_current": current_branch == "feature/login",
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

    def run_fwtm(self, schema=1, *, cwd=None, current_branch="feature/login", extra_env=None):
        env = {
            **os.environ,
            "PATH": f"{self.bin_dir}:{os.environ['PATH']}",
            "EXIT_CODE_SIGINT": "130",
            "FWTM_LIST_JSON": self.list_json(schema, current_branch=current_branch),
            "FWTM_FILTER_INPUT": str(self.filter_input),
            "FWTM_FILTER_BRANCH": "main",
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
            cwd=cwd or self.source,
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

    def assert_successful_merge(self, schema):
        result, values = self.run_fwtm(schema=schema)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "0", result.stderr)
        self.assertEqual(self.filter_input.read_text().splitlines(), [f"main\t{self.target}"])
        self.assertTrue((self.target / "feature.txt").exists())
        self.assertFalse(self.source.exists())
        self.assertEqual(self.git("branch", "--list", "feature/login").stdout, "")

    def test_merges_schema_1_selection_into_local_target_and_removes_source(self):
        self.assert_successful_merge(schema=1)

    def test_merges_schema_2_selection_into_local_target_and_removes_source(self):
        self.assert_successful_merge(schema=2)

    def test_merges_diverged_histories_and_removes_source(self):
        (self.target / "main.txt").write_text("main\n")
        self.git("add", "main.txt")
        self.git("commit", "-m", "test: main")

        result, values = self.run_fwtm()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "0", result.stderr)
        self.assertTrue((self.target / "main.txt").exists())
        self.assertTrue((self.target / "feature.txt").exists())
        merge_parents = self.git("rev-list", "--parents", "-n", "1", "HEAD").stdout.split()
        self.assertEqual(len(merge_parents), 3)
        self.assertFalse(self.source.exists())
        self.assertEqual(self.git("branch", "--list", "feature/login").stdout, "")

    def test_rejects_dirty_source_before_merging(self):
        (self.source / "dirty.txt").write_text("dirty\n")

        result, values = self.run_fwtm()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("統合元worktreeに未コミット変更があります", result.stderr)
        self.assertFalse((self.target / "feature.txt").exists())
        self.assertTrue(self.source.exists())

    def test_rejects_dirty_target_before_merging(self):
        (self.target / "dirty.txt").write_text("dirty\n")

        result, values = self.run_fwtm()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("統合先worktreeに未コミット変更があります", result.stderr)
        self.assertFalse((self.target / "feature.txt").exists())
        self.assertTrue(self.source.exists())

    def test_rejects_primary_worktree_as_source(self):
        result, values = self.run_fwtm(
            cwd=self.target,
            current_branch="main",
            extra_env={"FWTM_FILTER_BRANCH": "feature/login"},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "1", result.stderr)
        self.assertIn("primary worktreeからは統合できません", result.stderr)
        self.assertFalse(self.filter_input.exists())
        self.assertTrue(self.source.exists())

    def test_returns_sigint_when_selection_is_cancelled(self):
        result, values = self.run_fwtm(extra_env={"FWTM_FILTER_CANCEL": "1"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "130", result.stderr)
        self.assertTrue(self.source.exists())

    def test_returns_sigint_when_no_merge_candidate_exists(self):
        current_only = json.dumps(
            [
                {
                    "kind": "worktree",
                    "branch": "feature/login",
                    "path": str(self.source),
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
        self.assertTrue(self.source.exists())

    def test_preserves_wtl_failure_status_without_opening_the_picker(self):
        result, values = self.run_fwtm(extra_env={"FWTM_WTL_STATUS": "23"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["__STATUS"], "23", result.stderr)
        self.assertFalse(self.filter_input.exists())
        self.assertTrue(self.source.exists())


if __name__ == "__main__":
    unittest.main()
