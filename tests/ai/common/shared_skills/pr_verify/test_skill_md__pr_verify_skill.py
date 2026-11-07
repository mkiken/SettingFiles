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
            "Never push to the original\nor PR branch",
            "Commit only on the verification branch",
            "delete the verification branch or its remote ref",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, content)

    def test_publication_requires_approval_and_verified_push(self):
        content = (SKILL / "SKILL.md").read_text()
        for requirement in (
            "Local commit approval does not\n  authorize pushing or updating the PR body",
            "Wait for explicit publication approval",
            "GitHub Actions run, Jenkins build/job and Slack notification links",
            "Do not trigger jobs or send Slack messages",
            "remaining concerns",
            "containing the saved verification commit SHA",
            "destination is the PR's base repository",
            "inspect push hooks and workflows",
            "Push that branch with `-u`",
            "remote ref matches the saved commit",
            "upstream matches the pushed branch",
            "Do not update the PR body unless push is verified",
            "gh pr edit <PR-number> --repo <base-owner/repo> --body-file <approved-body-file>",
            "Independently re-fetch the body",
            "stop without automatically retrying or reposting",
            "Never automatically delete published evidence on failure",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, content)

    def test_body_replacement_preserves_user_content_and_detects_conflicts(self):
        content = (SKILL / "SKILL.md").read_text()
        for requirement in (
            "<!-- pr-verify:start -->",
            "<!-- pr-verify:end -->",
            "With no markers, append the section",
            "with exactly one ordered pair",
            "Preserve all content outside the managed section",
            "Stop on incomplete, reversed or duplicate markers",
            "Re-read the PR body and head immediately before updating",
            "If either changed",
            "obtain approval again",
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
