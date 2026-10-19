"""cl-pci routing: run the PR comment implementer in the worktree that owns the PR branch."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT, sanitized_env


AI_FILTER = REPO_ROOT / "shell/zsh/filter/ai.zsh"
PR_URL = "https://github.com/owner/repo/pull/7#discussion_r1"
GIT_ENV = {
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
}


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True,
                   env={**os.environ, **GIT_ENV})


class PciRouteTest(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.root = Path(self._temp.name).resolve()
        self.log = self.root / "calls"
        self.bin = self.root / "bin"
        self.bin.mkdir()

        # SSH-alias remote with mixed case: slug matching must ignore host and case
        self.clone = self.root / "clone"
        self.clone.mkdir()
        git(self.clone, "init", "-q", "-b", "main")
        git(self.clone, "commit", "-q", "--allow-empty", "-m", "init")
        git(self.clone, "remote", "add", "origin", "git@github-personal:Owner/Repo.git")
        self.feature = self.root / "feature-wt"
        git(self.clone, "worktree", "add", "-q", "-b", "feature", str(self.feature))

        self.write_stub("herdr",
            "printf 'herdr %s\\n' \"$*\" >> \"$TEST_CALLS\"\n"
            "case \"$1 $2\" in\n"
            "  'pane list') printf '%s\\n' \"$TEST_PANES\" ;;\n"
            "  'workspace list') printf '{\"result\":{\"workspaces\":[]}}\\n' ;;\n"
            "  'workspace create') printf '{\"result\":{\"workspace\":{\"workspace_id\":\"new\"},\"root_pane\":{\"pane_id\":\"p0\"}}}\\n' ;;\n"
            "esac\n")
        self.write_stub("gh",
            "if [[ \"$1 $2\" == 'pr view' ]]; then printf '%s\\n' \"$TEST_HEAD\"; exit 0; fi\n"
            "printf 'gh %s (cwd=%s)\\n' \"$*\" \"$PWD\" >> \"$TEST_CALLS\"\n")
        self.write_stub("zoxide", "printf '%s\\n' \"$TEST_REPOS\"\n")

    def write_stub(self, name, body):
        path = self.bin / name
        path.write_text("#!/bin/bash\n" + body, encoding="utf-8")
        path.chmod(0o755)

    def run_route(self, *args, head="feature", repos=None, panes=None, pwd=None,
                  kind="herdr", picked=None):
        env = sanitized_env({
            **GIT_ENV,
            "SET": str(REPO_ROOT),
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "HERDR_BIN_PATH": str(self.bin / "herdr"),
            "TEST_CALLS": str(self.log),
            "TEST_HEAD": head,
            "TEST_REPOS": "\n".join(str(r) for r in (repos if repos is not None else [self.clone])),
            "TEST_PANES": panes or '{"result":{"panes":[]}}',
            "TEST_PICKED": str(picked or ""),
            "TEST_KIND": kind,
        })
        quoted = " ".join(f"'{a}'" for a in args)
        snippet = f'''
EXIT_CODE_SIGINT=130
source "{AI_FILTER}"
_ai_multiplexer_kind() {{ print -r -- "$TEST_KIND"; }}
cdq() {{ builtin cd -q "$1"; }}
_impl() {{ {{ printf 'impl'; printf '|%s' "$@"; printf '\\n'; }} >> "$TEST_CALLS"; }}
_herdr_run_in_new_tab() {{ {{ printf 'newtab'; printf '|%s' "$@"; printf '\\n'; }} >> "$TEST_CALLS"; }}
_herdr_wait_shell_ready() {{ return 0; }}
_review_window_git_name() {{ print -r -- label; }}
_freview_resolve_dirty_state() {{ return 0; }}
_filter_git_worktree_path() {{ print -r -- "$TEST_PICKED"; }}
cd "{pwd or self.root}"
_ai_pci_route _impl {quoted}
print -r -- "rc=$?"
'''
        result = subprocess.run(["/bin/zsh", "-fc", snippet], env=env, text=True,
                                capture_output=True)
        calls = self.log.read_text().splitlines() if self.log.exists() else []
        return result, calls

    def panes_in(self, cwd):
        return ('{"result":{"panes":[{"cwd":"%s","workspace_id":"ws1","tab_id":"ws1:t1",'
                '"pane_id":"ws1:p1"}]}}' % cwd)

    def test_non_url_argument_runs_in_place(self):
        result, calls = self.run_route("just text")
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertEqual(calls, ["impl|just text"])

    def test_outside_herdr_runs_in_place(self):
        result, calls = self.run_route(PR_URL, kind="")
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertEqual(calls, [f"impl|{PR_URL}"])

    def test_inside_target_worktree_runs_in_place(self):
        result, calls = self.run_route(PR_URL, pwd=self.feature)
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertEqual(calls, [f"impl|{PR_URL}"])

    def test_open_pane_focuses_workspace_and_adds_tab(self):
        result, calls = self.run_route(PR_URL, "do it", panes=self.panes_in(self.feature / "sub"))
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertIn("herdr workspace focus ws1", calls)
        newtab = [c for c in calls if c.startswith("newtab")]
        self.assertEqual(len(newtab), 1, calls)
        # # and the space in the instruction must survive the round trip through the new shell
        self.assertEqual(newtab[0],
            f"newtab|ws1|{self.feature}|label|_impl {PR_URL.replace('#', chr(92) + '#')} do\\ it||1")
        # Existing panes may host a running agent; sending keystrokes there would corrupt its input
        self.assertFalse(any(c.startswith("herdr pane run") for c in calls), calls)

    def test_checked_out_without_pane_creates_workspace_without_checkout(self):
        result, calls = self.run_route(PR_URL)
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertIn(f"herdr workspace create --label {self.feature.name} --cwd {self.feature} --focus", calls)
        self.assertTrue(any(c.startswith("herdr pane run p0 _impl") for c in calls), calls)
        self.assertFalse(any(c.startswith("gh ") for c in calls), calls)

    def test_branch_not_checked_out_picks_worktree_and_checks_out(self):
        other = self.root / "other-wt"
        git(self.clone, "worktree", "add", "-q", "-b", "scratch", str(other))
        result, calls = self.run_route(PR_URL, head="other-branch", picked=other)
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertIn(f"gh pr checkout 7 (cwd={other})", calls)
        self.assertIn(f"herdr workspace create --label {other.name} --cwd {other} --focus", calls)

    def test_no_local_clone_fails_without_side_effects(self):
        result, calls = self.run_route(PR_URL, repos=[])
        self.assertNotIn("rc=0", result.stdout)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
