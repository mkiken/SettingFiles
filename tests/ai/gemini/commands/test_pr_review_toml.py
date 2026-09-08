import unittest

from support import REPO_ROOT

PR_REVIEW_TOML = REPO_ROOT / "ai/gemini/commands/pr-review.toml"


class PrReviewTomlFailsafeMarkerTest(unittest.TestCase):
    """gm-pr-reviewがGEMINI.mdのSlash Command Failsafe用に起動文字列へ付け足す
    括弧マーカーは、スラッシュコマンド展開が成功した場合はレビュー指示として誤解釈
    されず捨てられる必要がある。その破棄指示と、既存の出力契約が残ることをピン留めする。
    """

    @classmethod
    def setUpClass(cls):
        cls.pr_review = PR_REVIEW_TOML.read_text(encoding="utf-8")

    def test_discards_failsafe_parenthetical(self):
        self.assertIn(
            "discard that parenthesized portion entirely",
            self.pr_review,
        )

    def test_still_uses_args_placeholder(self):
        # {{args}} 置換の枠組み自体は変えていないことの確認
        self.assertIn("{{args}}", self.pr_review)

    def test_keeps_output_file_write_instruction(self):
        # コミット48f99ec7「所見ゼロでも必ず書き出す」の延長線 — 第3層の側面防御は
        # この指示が残っている前提で成立する
        self.assertIn(
            "you MUST write the exact review markdown output to that path",
            self.pr_review,
        )


if __name__ == "__main__":
    unittest.main()
