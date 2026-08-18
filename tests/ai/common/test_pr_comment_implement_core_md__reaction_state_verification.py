import unittest

from support import REPO_ROOT


CORE = REPO_ROOT / "ai/common/pr_comment_implement_core.md"


class PrCommentImplementReactionStateVerificationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = CORE.read_text(encoding="utf-8")

        section_start = cls.content.index("### Verify the final reaction state")
        summary_start = cls.content.index("Final execution summary:")
        cls.section = cls.content[section_start:summary_start]

    def test_verification_heading_exists(self):
        self.assertIn("### Verify the final reaction state", self.content)

    def test_section_sits_between_abort_cleanup_and_final_summary(self):
        abort = self.content.index("### Abort or decline cleanup")
        verify = self.content.index("### Verify the final reaction state")
        summary = self.content.index("Final execution summary:")

        self.assertLess(abort, verify)
        self.assertLess(verify, summary)

    def test_expected_state_table_covers_every_outcome(self):
        for outcome in (
            "コミットのみ",
            "コミット & 親ブランチにマージ",
            "🎉 only",
            "🚀 only",
            "none",
        ):
            with self.subTest(outcome=outcome):
                self.assertIn(outcome, self.section)

    def test_reconciliation_reads_actual_state_via_get(self):
        self.assertIn('gh api "${REACTION_TARGET}/reactions"', self.section)
        self.assertIn("select(.user.login", self.section)

    def test_reconciliation_covers_both_directions(self):
        self.assertIn("-X POST -f content=", self.section)
        self.assertIn("-X DELETE", self.section)

    def test_step_is_mandatory_not_best_effort(self):
        self.assertIn("This step is mandatory", self.section)
        self.assertIn("never print the", self.section)
        self.assertIn("summary without either a verified matching state", self.section)

    def test_reconciliation_is_bounded_to_one_pass(self):
        self.assertIn("one reconcile pass", self.section)

    def test_skips_when_reaction_target_unset(self):
        self.assertIn("REACTION_TARGET", self.section)
        self.assertIn("⏭️", self.section)

    def test_summary_contract_calls_out_verified_state(self):
        self.assertIn("reaction result (the verified", self.content)
        self.assertIn("state, not the intended one), resolve", self.content)

    def test_self_login_is_already_derived_before_verification_step(self):
        derivation = self.content.index("SELF_LOGIN=$(gh api user")
        verify = self.content.index("### Verify the final reaction state")

        self.assertLess(derivation, verify)

    def test_codex_skill_receives_the_verification_step(self):
        codex_skill = (
            REPO_ROOT / "ai/codex/skills/pr-comment-implement/SKILL.md"
        ).read_text(encoding="utf-8")

        self.assertIn("### Verify the final reaction state", codex_skill)


if __name__ == "__main__":
    unittest.main()
