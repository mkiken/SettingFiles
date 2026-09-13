import unittest

from support import REPO_ROOT


class CommitConfirmationContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        content = (REPO_ROOT / "ai/common/prompt_base.md").read_text(
            encoding="utf-8"
        )
        cls.workflow = content.split("# Post-Implementation Workflow\n", 1)[1]

    def test_commit_still_requires_user_choice(self):
        self.assertIn("inspect the working tree, then ask whether", self.workflow)
        self.assertIn(
            "to commit and push, commit only, or leave changes uncommitted",
            self.workflow,
        )
        self.assertIn("Perform the selected git action", self.workflow)

    def test_fixed_menu_is_limited_to_claude_and_gemini(self):
        # Codex Default mode prohibits a multiple-choice permission question;
        # retain the existing fixed menu only for the other two platforms.
        menu = self.workflow.split("For Claude and Gemini, present exactly:", 1)[1]
        menu = menu.split("\n\nStage only", 1)[0]
        labels = [line for line in menu.splitlines() if line[:1].isdigit()]
        self.assertEqual(len(labels), 3)
        for label in ("コミットしてプッシュ", "コミットのみ", "コミットしない"):
            self.assertIn(label, menu)


if __name__ == "__main__":
    unittest.main()
