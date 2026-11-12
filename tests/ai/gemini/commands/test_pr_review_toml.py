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


class PrReviewTomlIncrementalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pr_review = PR_REVIEW_TOML.read_text(encoding="utf-8")

    def test_fetches_previous_review_commit_in_first_commands(self):
        first_commands = self.pr_review.split("CRITICAL: Run these commands FIRST", 1)[-1].split("```", 2)[1]
        self.assertIn("pulls/<PR_NUMBER>/reviews", first_commands)
        self.assertIn(".user.login", first_commands)

    def test_instructs_ask_user_for_incremental_re_review(self):
        self.assertIn("### Incremental Re-review Check", self.pr_review)
        self.assertIn("ask_user", self.pr_review)
        self.assertIn("差分のみ", self.pr_review)
        self.assertIn("PR全体", self.pr_review)

    def test_defines_ancestry_checks_before_asking(self):
        self.assertIn("git merge-base --is-ancestor", self.pr_review)
        self.assertIn("compare/<PREV_OID>...<headRefOid>", self.pr_review)


if __name__ == "__main__":
    unittest.main()
