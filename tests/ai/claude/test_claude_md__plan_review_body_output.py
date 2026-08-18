import unittest

from support import REPO_ROOT


CLAUDE_MD_PATH = REPO_ROOT / "ai/claude/_CLAUDE.md"


class PlanReviewBodyOutputTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.claude_md = CLAUDE_MD_PATH.read_text(encoding="utf-8")

    def test_instructs_outputting_the_plan_body_before_the_dialog(self):
        for required in (
            "output the plan file's current full content as ordinary assistant text",
            "not a summary or excerpt, the whole thing",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.claude_md)

    def test_output_is_not_wrapped_in_a_code_fence(self):
        self.assertIn("not wrapped in a code fence", self.claude_md)

    def test_body_output_and_dialog_share_the_same_turn(self):
        self.assertIn("in this same turn", self.claude_md)

    def test_double_appearance_with_exit_plan_mode_is_pinned_as_intentional(self):
        # Negative-pin rationale: ExitPlanMode re-renders the same plan file on
        # its own approval surface. Without this explicit "intentional, not
        # redundant" note, a later token-shortening pass could read the
        # pre-dialog output as duplicate and delete it, silently regressing
        # to the pre-fix ordering the user asked to change.
        for required in (
            "intentional, not redundant",
            "do not collapse the two into one by skipping this output",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.claude_md)

    def test_body_output_precedes_the_dig_html_dialog(self):
        before_dialog = self.claude_md.split(
            "Then merge the dig/HTML choice with the Plan Review Presentation offer"
        )[0]
        self.assertIn(
            "output the plan file's current full content as ordinary assistant text",
            before_dialog,
        )

    def test_mechanical_plans_still_skip_straight_to_exit_plan_mode_with_no_output(self):
        self.assertIn(
            "skip straight to `ExitPlanMode` with no dialog", self.claude_md
        )

    def test_four_dialog_options_are_intact(self):
        for required in (
            "Both: open the browser and also run dig.",
            "dig only: run dig without opening the browser.",
            "Open the browser now, decide on dig after reading.",
            "Neither.",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.claude_md)


if __name__ == "__main__":
    unittest.main()
