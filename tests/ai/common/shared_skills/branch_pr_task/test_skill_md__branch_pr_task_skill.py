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

    def test_dirty_or_detached_worktree_stops_without_workaround(self):
        for required in (
            "detached",
            "git status --porcelain",
            "Never stash, clean, reset, or commit",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.content)

    def test_branch_is_cut_from_confirmed_parent(self):
        self.assertIn("git switch -c <branch> origin/<parent>", self.content)
        self.assertIn("git fetch origin", self.content)
        # The parent is proposed first, then corrected by the user.
        self.assertLess(
            self.content.index("Choose the parent branch"),
            self.content.index("git switch -c"),
        )

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

    def test_pr_body_background_is_conditional_and_focus_points_kept(self):
        self.assertIn("## 背景・目的", self.content)
        self.assertIn("Omit the whole section otherwise", self.content)
        self.assertIn("## Review Focus Points", self.content)


if __name__ == "__main__":
    unittest.main()
