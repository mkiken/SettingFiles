import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


from support import REPO_ROOT
SCRIPT = REPO_ROOT / "shell/tmux/herdr-create-worktree-tab.sh"
ZSH = shutil.which("zsh")


class HerdrCreateWorktreeTabTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.source = self.root / "source"
        self.worktree = self.root / "feature-worktree"
        self.source.mkdir()
        self.worktree.mkdir()
        self.call_log = self.root / "calls.log"

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_script(
        self,
        *,
        input_text: str,
        active_pane_id: str = "w7:p3",
        active_pane_cwd: str | None = None,
        wtc_status: int = 0,
        tab_status: int = 0,
        extra_env: dict | None = None,
    ) -> subprocess.CompletedProcess[str]:
        active_pane_cwd = str(self.source) if active_pane_cwd is None else active_pane_cwd
        script = f'''\
wtc() {{
  print -r -- "wtc:$*" >> "{self.call_log}"
  builtin cd "{self.worktree}"
  return {wtc_status}
}}
_herdr_run_in_new_tab() {{
  print -r -- "newtab:$*" >> "{self.call_log}"
  return {tab_status}
}}
source "{SCRIPT}"
exit_code=$?
print -r -- "__STATUS=$exit_code"
'''
        env = {
            **os.environ,
            "HERDR_ENV": "1",
            "HERDR_ACTIVE_PANE_ID": active_pane_id,
            "HERDR_ACTIVE_PANE_CWD": active_pane_cwd,
            **(extra_env or {}),
        }
        return subprocess.run(
            [ZSH, "-fc", script],
            cwd=REPO_ROOT,
            env=env,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
        )

    def read_calls(self) -> list[str]:
        return self.call_log.read_text().splitlines() if self.call_log.exists() else []

    def test_creates_worktree_then_opens_focused_tab_in_source_workspace(self):
        result = self.run_script(input_text="feature/demo\n")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("__STATUS=0", result.stdout)
        self.assertEqual(
            self.read_calls(),
            [
                "wtc:feature/demo",
                f"newtab:w7 {self.worktree} feature/demo :  1",
            ],
        )

    def test_empty_branch_cancels_without_creating_a_worktree_or_tab(self):
        result = self.run_script(input_text="\n")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("__STATUS=0", result.stdout)
        self.assertEqual(self.read_calls(), [])

    def test_missing_active_pane_context_fails_without_side_effects(self):
        result = self.run_script(input_text="feature/demo\n", active_pane_cwd="")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("__STATUS=1", result.stdout)
        self.assertIn("active pane context is unavailable", result.stderr)
        self.assertEqual(self.read_calls(), [])

    def test_worktree_creation_failure_does_not_open_a_tab(self):
        result = self.run_script(input_text="feature/demo\n", wtc_status=17)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("__STATUS=17", result.stdout)
        self.assertEqual(self.read_calls(), ["wtc:feature/demo"])

    def test_tab_creation_failure_preserves_the_created_worktree(self):
        result = self.run_script(input_text="feature/demo\n", tab_status=23)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("__STATUS=23", result.stdout)
        self.assertEqual(
            self.read_calls(),
            [
                "wtc:feature/demo",
                f"newtab:w7 {self.worktree} feature/demo :  1",
            ],
        )

    def test_pause_writes_mark_when_provided(self):
        with tempfile.NamedTemporaryFile() as mark:
            result = self.run_script(
                input_text="feature/demo\n",
                wtc_status=17,
                extra_env={"HERDR_POPUP_PAUSE_MARK": mark.name},
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("__STATUS=17", result.stdout)
            self.assertTrue(Path(mark.name).stat().st_size > 0)

    def test_pause_is_a_no_op_without_mark(self):
        result = self.run_script(input_text="feature/demo\n", wtc_status=17)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("__STATUS=17", result.stdout)

    def test_pause_swallows_unwritable_mark_path(self):
        result = self.run_script(
            input_text="feature/demo\n",
            wtc_status=17,
            extra_env={"HERDR_POPUP_PAUSE_MARK": "/nonexistent-dir/mark"},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("__STATUS=17", result.stdout)
