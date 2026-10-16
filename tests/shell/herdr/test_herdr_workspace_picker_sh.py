"""Herdr workspace/tab picker listing with git branches."""

import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT, sanitized_env


SCRIPT = REPO_ROOT / "shell/herdr/herdr-workspace-picker.sh"
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def git(cwd, *args):
    subprocess.run(
        ["git", "-C", str(cwd), *args], check=True, capture_output=True,
        env=sanitized_env({"GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1"}),
    )


def make_repo(path, branch):
    path.mkdir(parents=True)
    git(path, "init", "-q", "-b", branch)
    git(path, "-c", "user.name=t", "-c", "user.email=t@example.invalid",
        "commit", "-q", "--allow-empty", "-m", "init")
    return path


class HerdrWorkspacePickerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.log = self.root / "calls"
        self.fake = self.root / "fake-herdr"
        self.fake.write_text(
            "#!/bin/bash\n"
            "printf '%s\\n' \"$*\" >> \"$TEST_CALLS\"\n"
            "case \"$1 $2\" in\n"
            "  'workspace list') [[ ${TEST_LIST_FAIL:-0} == 1 ]] && exit 1; "
            "printf '%s\\n' \"$TEST_WORKSPACES\" ;;\n"
            "  'tab list') [[ ${TEST_TAB_LIST_FAIL:-0} == 1 ]] && exit 1; "
            "printf '%s\\n' \"$TEST_TABS\" ;;\n"
            "  'pane list') printf '%s\\n' \"$TEST_PANES\" ;;\n"
            "  *) exit 9 ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        self.fake.chmod(0o755)
        # PATH 上の herdr が呼ばれたら痕跡を残す罠。HERDR_BIN_PATH の stub だけが使われることを確かめる。
        self.trap_bin = self.root / "trap-bin"
        self.trap_bin.mkdir()
        self.trap_log = self.root / "trap-called"
        trap = self.trap_bin / "herdr"
        trap.write_text(f"#!/bin/bash\ntouch '{self.trap_log}'\nexit 1\n", encoding="utf-8")
        trap.chmod(0o755)
        self.home = self.root / "home"
        self.home.mkdir()

    def run_list(self, workspaces, panes, tabs=(), **env_extra):
        env = sanitized_env({
            "HERDR_BIN_PATH": str(self.fake),
            "HOME": str(self.home),
            "PATH": f"{self.trap_bin}:/usr/bin:/bin",
            "TEST_CALLS": str(self.log),
            "TEST_WORKSPACES": json.dumps({"result": {"workspaces": workspaces}}),
            "TEST_TABS": json.dumps({"result": {"tabs": list(tabs)}}),
            "TEST_PANES": json.dumps({"result": {"panes": panes}}),
            **env_extra,
        })
        result = subprocess.run(
            [str(SCRIPT), "--list"], capture_output=True, text=True, env=env,
        )
        self.assertFalse(self.trap_log.exists(), "herdr on PATH must not be invoked")
        rows = [ANSI.sub("", line).split("\t", 1) for line in result.stdout.splitlines()]
        return result, rows

    @staticmethod
    def workspace(ws_id, label, tab, focused=False):
        return {"workspace_id": ws_id, "label": label, "active_tab_id": tab, "focused": focused}

    @staticmethod
    def tab(tab_id, ws_id, label, number, focused=False):
        return {"tab_id": tab_id, "workspace_id": ws_id, "label": label,
                "number": number, "focused": focused}

    @staticmethod
    def pane(pane_id, tab, cwd, focused=False):
        return {"pane_id": pane_id, "tab_id": tab, "cwd": cwd,
                "foreground_cwd": "/somewhere/else", "focused": focused}

    def test_rows_show_branch_and_home_relative_cwd_with_focused_last(self):
        repo_a = make_repo(self.home / "src/a", "feature-a")
        repo_b = make_repo(self.root / "b", "main")
        result, rows = self.run_list(
            [self.workspace("w1", "[1] a", "w1:t1", focused=True),
             self.workspace("w2", "[2] b", "w2:t1")],
            [self.pane("w1:p1", "w1:t1", str(repo_a)),
             self.pane("w2:p1", "w2:t1", str(repo_b))],
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(rows, [
            ["ws:w2", f"  [2] b  main  {repo_b}"],
            ["ws:w1", "* [1] a  feature-a  ~/src/a"],
        ])
        self.assertEqual(self.log.read_text().splitlines(),
                         ["workspace list", "tab list", "pane list"])

    def test_focused_pane_of_active_tab_wins_over_first_pane(self):
        first = make_repo(self.root / "first", "first-branch")
        chosen = make_repo(self.root / "chosen", "chosen-branch")
        other_tab = make_repo(self.root / "other", "other-branch")
        result, rows = self.run_list(
            [self.workspace("w1", "[1] x", "w1:t2")],
            [self.pane("w1:p0", "w1:t1", str(other_tab), focused=True),
             self.pane("w1:p1", "w1:t2", str(first)),
             self.pane("w1:p2", "w1:t2", str(chosen), focused=True)],
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(rows, [["ws:w1", f"  [1] x  chosen-branch  {chosen}"]])

    def test_detached_head_shows_short_sha(self):
        repo = make_repo(self.root / "r", "main")
        git(repo, "checkout", "-q", "--detach")
        sha = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, check=True,
                             env=sanitized_env()).stdout.strip()
        result, rows = self.run_list(
            [self.workspace("w1", "[1] r", "w1:t1")],
            [self.pane("w1:p1", "w1:t1", str(repo))],
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(rows, [["ws:w1", f"  [1] r  {sha}  {repo}"]])

    def test_non_git_or_missing_cwd_lists_without_branch(self):
        plain = self.root / "plain"
        plain.mkdir()
        result, rows = self.run_list(
            [self.workspace("w1", "[1] plain", "w1:t1"),
             self.workspace("w2", "[2] nopane", "w2:t1")],
            [self.pane("w1:p1", "w1:t1", str(plain))],
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(rows, [["ws:w1", f"  [1] plain  {plain}"], ["ws:w2", "  [2] nopane"]])

    def test_tabs_are_listed_under_their_workspace_in_number_order(self):
        repo_a = make_repo(self.root / "a", "branch-a")
        repo_b = make_repo(self.root / "b", "branch-b")
        repo_c = make_repo(self.root / "c", "branch-c")
        result, rows = self.run_list(
            [self.workspace("w1", "[1] alpha", "w1:t1", focused=True),
             self.workspace("w2", "[2] beta", "w2:t1")],
            [self.pane("w1:p1", "w1:t1", str(repo_a)),
             self.pane("w2:p1", "w2:t1", str(repo_b)),
             self.pane("w2:p2", "w2:t2", str(repo_c))],
            tabs=[self.tab("w2:t2", "w2", "[2] second", 2),
                  self.tab("w2:t1", "w2", "[1] first", 1),
                  self.tab("w1:t1", "w1", "[1] only", 1, focused=True)],
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        # 現在の workspace は tab ごと末尾。tab 行は親 workspace 名を @ 付きで持つ。
        self.assertEqual(rows, [
            ["ws:w2", f"  [2] beta  branch-b  {repo_b}"],
            ["tab:w2:t1", f"    └ [1] first  branch-b  {repo_b}  @beta"],
            ["tab:w2:t2", f"    └ [2] second  branch-c  {repo_c}  @beta"],
            ["ws:w1", f"* [1] alpha  branch-a  {repo_a}"],
            ["tab:w1:t1", f"*   └ [1] only  branch-a  {repo_a}  @alpha"],
        ])

    def test_tab_without_panes_lists_without_branch(self):
        result, rows = self.run_list(
            [self.workspace("w1", "[1] a", "w1:t1")],
            [],
            tabs=[self.tab("w1:t1", "w1", "[1] t", 1)],
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(rows, [["ws:w1", "  [1] a"], ["tab:w1:t1", "    └ [1] t  @a"]])

    def test_tab_list_failure_fails_loudly(self):
        result, _ = self.run_list(
            [self.workspace("w1", "[1] a", "w1:t1")], [], TEST_TAB_LIST_FAIL="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("failed", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_workspace_list_failure_or_invalid_json_fails_loudly(self):
        for extra, message in (({"TEST_LIST_FAIL": "1"}, "failed"),
                               ({"TEST_WORKSPACES": "{bad"}, "invalid JSON")):
            with self.subTest(extra=extra):
                env_extra = dict(extra)
                if "TEST_WORKSPACES" in env_extra:
                    # run_list の既定値を上書きするため直接実行する。
                    env = sanitized_env({
                        "HERDR_BIN_PATH": str(self.fake), "HOME": str(self.home),
                        "PATH": f"{self.trap_bin}:/usr/bin:/bin",
                        "TEST_CALLS": str(self.log), "TEST_TABS": "{}", "TEST_PANES": "{}",
                        **env_extra,
                    })
                    result = subprocess.run([str(SCRIPT), "--list"], capture_output=True,
                                            text=True, env=env)
                else:
                    result, _ = self.run_list([], [], **env_extra)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
                self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
