import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT, sanitized_env

SCRIPT = REPO_ROOT / "shell" / "common" / "pr" / "ai_review_cleanup_worktree.sh"
BRANCH = "pr-branch"


class CleanupWorktreeTest(unittest.TestCase):
    """使い捨てのbare remote + cloneだけを相手にする（実リポジトリは触らない）。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        # macOSの/tmpはsymlinkなので、git worktree listの実パスと揃える
        base = Path(self.tmp.name).resolve()
        self.env = sanitized_env(
            GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
            GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid",
            GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null",
        )
        self.remote = base / "origin.git"
        self.main = base / "main"
        self.worktree = base / "review-wt"
        self.run_dir = base / "run"
        self.run_dir.mkdir()
        self.marker = self.run_dir / "temp_worktree"

        self.git(base, "init", "-q", "--bare", "-b", "main", str(self.remote))
        self.git(base, "clone", "-q", str(self.remote), str(self.main))
        (self.main / "a.txt").write_text("a\n")
        self.git(self.main, "add", "a.txt")
        self.git(self.main, "commit", "-q", "-m", "init")
        self.git(self.main, "push", "-q", "origin", "main")
        # PRのheadブランチ: remoteにpush済みのコミットを1つ持つ
        self.git(self.main, "switch", "-q", "-c", BRANCH)
        (self.main / "b.txt").write_text("b\n")
        self.git(self.main, "add", "b.txt")
        self.git(self.main, "commit", "-q", "-m", "pr commit")
        self.git(self.main, "push", "-q", "origin", BRANCH)
        self.git(self.main, "switch", "-q", "main")
        self.git(self.main, "worktree", "add", "-q", str(self.worktree), BRANCH)

    def git(self, cwd, *args):
        return subprocess.run(
            ["git", *args], cwd=cwd, env=self.env, check=True, capture_output=True, text=True
        ).stdout

    def write_marker(self, path=None, branch=BRANCH):
        self.marker.write_text(f"{path or self.worktree}\n{branch}\n")

    def run_script(self):
        return subprocess.run(
            ["bash", str(SCRIPT), str(self.run_dir)],
            env=self.env, capture_output=True, text=True,
        )

    def branches(self):
        return self.git(self.main, "branch", "--format=%(refname:short)").split()

    def test_clean_and_pushed_removes_worktree_and_new_branch(self):
        self.write_marker()
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.worktree.exists())
        self.assertNotIn(BRANCH, self.branches())
        self.assertFalse(self.marker.exists())

    def test_branch_not_recorded_as_new_is_kept(self):
        # 作成前から存在したブランチ（2行目が空）はユーザー資産なので消さない
        self.write_marker(branch="")
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.worktree.exists())
        self.assertIn(BRANCH, self.branches())

    def test_untracked_file_keeps_worktree_and_marker(self):
        (self.worktree / "scratch.txt").write_text("wip\n")
        self.write_marker()
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.worktree.exists())
        self.assertIn(BRANCH, self.branches())
        self.assertTrue(self.marker.exists())
        self.assertIn("未コミットの変更", result.stdout)

    def test_modified_tracked_file_keeps_worktree(self):
        (self.worktree / "b.txt").write_text("changed\n")
        self.write_marker()
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.worktree.exists())

    def test_unpushed_commit_keeps_worktree_and_branch(self):
        (self.worktree / "c.txt").write_text("c\n")
        self.git(self.worktree, "add", "c.txt")
        self.git(self.worktree, "commit", "-q", "-m", "local only")
        self.write_marker()
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.worktree.exists())
        self.assertIn(BRANCH, self.branches())
        self.assertTrue(self.marker.exists())
        self.assertIn("pushされていないコミット", result.stdout)

    def test_missing_marker_is_a_noop(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertTrue(self.worktree.exists())

    def test_already_removed_worktree_clears_marker(self):
        self.git(self.main, "worktree", "remove", str(self.worktree))
        self.write_marker()
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.marker.exists())

    def test_main_worktree_is_never_removed(self):
        # マーカーが壊れてメインworktreeを指しても削除しない
        self.write_marker(path=self.main, branch="")
        result = self.run_script()
        self.assertEqual(result.returncode, 1)
        self.assertTrue((self.main / "a.txt").exists())
        self.assertTrue(self.marker.exists())


if __name__ == "__main__":
    unittest.main()
