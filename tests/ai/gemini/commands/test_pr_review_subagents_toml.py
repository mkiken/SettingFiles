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


class PrReviewSubagentsTomlIncrementalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pr_review_subagents = PR_REVIEW_SUBAGENTS_TOML.read_text(encoding="utf-8")

    def test_fetches_previous_review_commit_in_first_commands(self):
        first_commands = self.pr_review_subagents.split("Run with `run_shell_command`:", 1)[-1].split("```", 2)[1]
        self.assertIn("pulls/<PR_NUMBER>/reviews", first_commands)
        self.assertIn(".user.login", first_commands)

    def test_incremental_check_precedes_launch_agents(self):
        check_pos = self.pr_review_subagents.find("### Incremental Re-review Check")
        launch_pos = self.pr_review_subagents.find("## Launch Agents")
        self.assertGreater(check_pos, -1, "Incremental check heading must exist")
        self.assertGreater(launch_pos, -1, "Launch Agents heading must exist")
        self.assertLess(check_pos, launch_pos, "Incremental check must come BEFORE Launch Agents")

    def test_instructs_ask_user_for_incremental_re_review(self):
        self.assertIn("ask_user", self.pr_review_subagents)
        self.assertIn("差分のみ", self.pr_review_subagents)
        self.assertIn("PR全体", self.pr_review_subagents)

    def test_defines_ancestry_checks_before_asking(self):
        self.assertIn("git merge-base --is-ancestor", self.pr_review_subagents)
        self.assertIn("compare/<PREV_OID>...<headRefOid>", self.pr_review_subagents)


if __name__ == "__main__":
    unittest.main()
