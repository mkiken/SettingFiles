import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT, sanitized_env


SKILL = REPO_ROOT / "ai/common/shared_skills/pr-verify"


class PrVerifyContractTest(unittest.TestCase):
    def test_platform_links_and_metadata(self):
        for platform in ("claude", "codex"):
            link = REPO_ROOT / f"ai/{platform}/skills/pr-verify"
            self.assertTrue(link.is_symlink())
            self.assertEqual(os.readlink(link), "../../common/shared_skills/pr-verify")
            self.assertEqual(link.resolve(), SKILL.resolve())
        self.assertIn("$pr-verify", (SKILL / "agents/openai.yaml").read_text())

    def test_workflow_preserves_approval_and_safety_boundaries(self):
        content = (SKILL / "SKILL.md").read_text()
        for requirement in (
            "Wait for explicit approval before creating the worktree",
            "Changed scope, safety boundaries or test",
            "git worktree add -b <verification-branch> <verification-path> <pinned-head-sha>",
            "Do not inherit live service credentials",
            "Do not send real\nnotifications",
            "disable user, group and\nbroadcast mentions",
            "`テスト通知`",
            "Neutralize mention markup",
            "Stop execution, report the reproduction",
            "obtain approval before fixing",
            "never pushes, merges, or posts to the PR",
            "Commit only on the verification branch",
            "Never delete the verification branch",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, content)


class PrVerifyGitIsolationTest(unittest.TestCase):
    def test_dirty_origin_snapshot_collision_and_saved_branch(self):
        # Exercise cleanup only in a disposable repository, never this checkout.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            origin = root / "origin"
            origin.mkdir()
            env = sanitized_env({
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_AUTHOR_NAME": "test",
                "GIT_AUTHOR_EMAIL": "test@example.invalid",
                "GIT_COMMITTER_NAME": "test",
                "GIT_COMMITTER_EMAIL": "test@example.invalid",
            })

            def git(*args, cwd=origin, check=True):
                return subprocess.run(
                    ["git", *args], cwd=cwd, env=env, check=check,
                    capture_output=True, text=True,
                )

            git("init", "-b", "main")
            git("config", "core.hooksPath", str(root / "no-hooks"))
            (origin / "feature.txt").write_text("PR snapshot\n")
            git("add", "feature.txt")
            git("commit", "-m", "initial")
            pinned = git("rev-parse", "HEAD").stdout.strip()
            (origin / "feature.txt").write_text("uncommitted user work\n")
            before = git("status", "--porcelain").stdout
            worktree = root / "verification"
            branch = "verify/pr-123-test"
            git("worktree", "add", "-b", branch, str(worktree), pinned)
            self.assertEqual((worktree / "feature.txt").read_text(), "PR snapshot\n")
            collision = git("worktree", "add", "-b", branch, str(root / "collision"), pinned, check=False)
            self.assertNotEqual(collision.returncode, 0)

            # A later PR commit must not silently replace the pinned snapshot.
            git("commit", "--allow-empty", "-m", "updated PR")
            updated = git("rev-parse", "HEAD").stdout.strip()
            self.assertNotEqual(updated, pinned)
            self.assertEqual(git("rev-parse", "HEAD", cwd=worktree).stdout.strip(), pinned)
            (worktree / "verification.txt").write_text("synthetic verification evidence\n")
            refused = git("worktree", "remove", str(worktree), check=False)
            self.assertNotEqual(refused.returncode, 0)
            self.assertTrue(worktree.exists())
            git("add", "verification.txt", cwd=worktree)
            git("commit", "-m", "save verification", cwd=worktree)
            saved = git("rev-parse", "HEAD", cwd=worktree).stdout.strip()
            git("worktree", "remove", str(worktree))
            self.assertFalse(worktree.exists())
            self.assertEqual(git("rev-parse", branch).stdout.strip(), saved)
            self.assertEqual(git("show", f"{branch}:verification.txt").stdout, "synthetic verification evidence\n")
            self.assertEqual(git("rev-parse", "HEAD").stdout.strip(), updated)
            self.assertEqual(git("branch", "--show-current").stdout.strip(), "main")
            self.assertEqual(git("status", "--porcelain").stdout, before)
            self.assertEqual((origin / "feature.txt").read_text(), "uncommitted user work\n")
