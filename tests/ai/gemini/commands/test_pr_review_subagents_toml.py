import unittest

from support import REPO_ROOT

PR_REVIEW_SUBAGENTS_TOML = REPO_ROOT / "ai/gemini/commands/pr-review-subagents.toml"


class PrReviewSubagentsTomlFailsafeMarkerTest(unittest.TestCase):
    """gm-pr-review-subagentがGEMINI.mdのSlash Command Failsafe用に起動文字列へ
    付け足す括弧マーカーは、スラッシュコマンド展開が成功した場合はレビュー指示として
    誤解釈されず捨てられる必要がある。その破棄指示と、既存の出力契約が残ることを
    ピン留めする。
    """

    @classmethod
    def setUpClass(cls):
        cls.pr_review_subagents = PR_REVIEW_SUBAGENTS_TOML.read_text(encoding="utf-8")

    def test_discards_failsafe_parenthetical(self):
        self.assertIn(
            "discard that parenthesized portion entirely",
            self.pr_review_subagents,
        )

    def test_still_uses_args_placeholder(self):
        self.assertIn("{{args}}", self.pr_review_subagents)

    def test_keeps_output_file_write_instruction(self):
        self.assertIn(
            "you MUST write the exact review markdown output to that path",
            self.pr_review_subagents,
        )


if __name__ == "__main__":
    unittest.main()
