import unittest

from support import REPO_ROOT

CORE = REPO_ROOT / "ai/common/pr_create_by_branch_core.md"
REMINDER_TEXT = "リマインド: PRのレビュワー設定を忘れないでください。"


class PrCreateByBranchReviewerReminderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = CORE.read_text(encoding="utf-8")

    def test_reminder_line_present(self):
        self.assertIn(REMINDER_TEXT, self.content)

    def test_reminder_placed_after_success_block(self):
        success_pos = self.content.index("On success:")
        create_heading_pos = self.content.index("## Create PR")
        reminder_pos = self.content.index(REMINDER_TEXT)
        self.assertGreater(reminder_pos, success_pos)
        self.assertGreater(reminder_pos, create_heading_pos)

    def test_reminder_not_inside_confirm_gate(self):
        # 対話式の確認選択肢へリマインドを混ぜる案は明示的に却下されている。
        # Confirmの4択ゲートとCreate PR見出しの間にリマインドが無いことを固定する
        confirm_pos = self.content.index("## Confirm")
        create_pos = self.content.index("## Create PR")
        confirm_block = self.content[confirm_pos:create_pos]
        self.assertNotIn(REMINDER_TEXT, confirm_block)

    def test_does_not_check_existing_reviewers(self):
        # 「常に出す・検出しない」というユーザー決定を固定する。
        # reviewRequests等での設定済み判定は不要と明示的に却下されている
        self.assertNotIn("reviewRequests", self.content)

    def test_confirm_options_unchanged(self):
        for option in (
            "はい、作成する",
            "titleを修正したい",
            "bodyを修正したい",
            "キャンセル",
        ):
            with self.subTest(option=option):
                self.assertIn(option, self.content)

    def test_codex_generated_skill_carries_the_reminder(self):
        codex_skill = (
            REPO_ROOT / "ai/codex/skills/pr-create-by-branch/SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn(REMINDER_TEXT, codex_skill)

    def test_claude_adapter_includes_core_at_runtime(self):
        claude_skill = (
            REPO_ROOT / "ai/claude/skills/pr-create-by-branch/SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("~/.claude/common/pr_create_by_branch_core.md", claude_skill)


if __name__ == "__main__":
    unittest.main()
