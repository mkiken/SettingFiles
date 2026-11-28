import os
import unittest
from pathlib import Path

from support import REPO_ROOT

SHARED_SKILL = REPO_ROOT / "ai/common/shared_skills/branch-pr-task"
PLATFORM_LINK_TARGET = Path("../../common/shared_skills/branch-pr-task")
REMINDER_TEXT = "リマインド: PRのレビュワー設定を忘れないでください。"


class BranchPrTaskDeploymentTest(unittest.TestCase):
    def test_claude_and_codex_link_to_shared_skill(self):
        for platform in ("claude", "codex"):
            with self.subTest(platform=platform):
                link = REPO_ROOT / f"ai/{platform}/skills/branch-pr-task"
                self.assertTrue(link.is_symlink())
                self.assertEqual(Path(os.readlink(link)), PLATFORM_LINK_TARGET)
                self.assertEqual(link.resolve(), SHARED_SKILL.resolve())
                self.assertTrue((link / "SKILL.md").is_file())

    def test_gemini_is_excluded(self):
        # Gemini has no `$skill` invocation or user-confirmation primitive wired
        # to this workflow; selective sharing covers only Claude and Codex.
        self.assertFalse((REPO_ROOT / "ai/gemini/skills/branch-pr-task").exists())


class BranchPrTaskContentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = (SHARED_SKILL / "SKILL.md").read_text(encoding="utf-8")

    def test_metadata_and_ui_configuration_exist(self):
        self.assertIn("name: branch-pr-task", self.content)
        self.assertIn("$branch-pr-task <implementation request>", self.content)

        openai_yaml = (SHARED_SKILL / "agents/openai.yaml").read_text(encoding="utf-8")
        self.assertIn('display_name: "Branch PR Task"', openai_yaml)
        self.assertIn("$branch-pr-task", openai_yaml)
        self.assertIn("new worktree", openai_yaml)

    def test_dirty_worktree_requires_confirmation_and_detached_stops(self):
        for required in (
            "detached", "git status --porcelain", "そのまま進める", "中止する",
            "Continue only on explicit", "Never stash, clean, reset, or commit",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.content)
        self.assertLess(self.content.index("そのまま進める"), self.content.index("git worktree add"))

    def test_worktree_is_cut_from_confirmed_parent(self):
        self.assertIn("git worktree add --track -b <branch> <path> origin/<parent>", self.content)
        self.assertIn("git fetch origin", self.content)
        self.assertLess(self.content.index("Choose the parent branch"), self.content.index("git worktree add"))
        for required in ("replacing `/` with `-`", "Display the resolved path", "path already exists",
                         "exactly one registered worktree", "verification mismatch"):
            with self.subTest(required=required):
                self.assertIn(required, self.content)

    def test_parent_and_branch_name_are_asked_as_separate_questions(self):
        section = self.content[
            self.content.index("## Choose the parent branch") : self.content.index("## Create the worktree")
        ]
        for required in ("two separate questions", "- Parent branch:", "- Branch name:"):
            with self.subTest(required=required):
                self.assertIn(required, section)

    def test_cleanup_depends_on_result(self):
        empty = self.content[self.content.index("If the worktree is clean") : self.content.index("## Confirm once")]
        for required in ("recorded starting commit", "git worktree remove <path>",
                         "git branch -d <branch>", "both are absent", "additional commits"):
            with self.subTest(required=required):
                self.assertIn(required, empty)
        success = self.content[self.content.index("After all checks pass") : self.content.index("## Report")]
        for required in ("git worktree remove <path>", "PR branch still exists", "Keep the branch",
                         "cancellation, failure, remaining files, or additional commits"):
            with self.subTest(required=required):
                self.assertIn(required, success)

    def test_confirmation_precedes_commit_push_and_pr(self):
        confirm_pos = self.content.index("## Confirm once")
        for step in ("git push -u origin", "gh pr create"):
            with self.subTest(step=step):
                self.assertGreater(self.content.index(step), confirm_pos)
        for option in (
            "はい、作成する",
            "titleを修正したい",
            "bodyを修正したい",
            "キャンセル",
        ):
            with self.subTest(option=option):
                self.assertIn(option, self.content)

    def test_pr_targets_parent_with_stdin_body_and_no_force(self):
        self.assertIn('--base <parent>', self.content)
        self.assertIn("--body-file -", self.content)
        self.assertIn("without force", self.content)
        self.assertNotIn("--force", self.content)

    def test_remote_and_base_are_verified_after_creation(self):
        for required in ("git ls-remote origin <branch>", "baseRefName"):
            with self.subTest(required=required):
                self.assertIn(required, self.content)

    def test_reviewer_reminder_is_after_creation_and_unconditional(self):
        create_pos = self.content.index("gh pr create")
        confirm_block = self.content[
            self.content.index("## Confirm once") : self.content.index("## Commit, push")
        ]
        self.assertGreater(self.content.index(REMINDER_TEXT), create_pos)
        self.assertNotIn(REMINDER_TEXT, confirm_block)
        # Reviewer detection was rejected for pr-create-by-branch; keep the
        # same "always remind, never check or assign" decision here.
        self.assertNotIn("reviewRequests", self.content)

    def test_pr_title_and_body_follow_pr_create_by_branch(self):
        self.assertIn("### PR title and body", self.content)
        self.assertIn("`pr-create-by-branch` skill", self.content)
        self.assertIn("Review Focus Points", self.content)
        # The duplicated body template was removed so PR rules live in one place.
        self.assertNotIn("## 背景・目的", self.content)


if __name__ == "__main__":
    unittest.main()
