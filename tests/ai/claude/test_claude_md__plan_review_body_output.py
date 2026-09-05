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

    def test_two_gates_must_both_hold_before_offering(self):
        for required in (
            "offer both only when two gates both hold",
            "Gate 1 — content",
            "undecided design decision or trade-off",
            "spans 3+ files or crosses subsystem/module boundaries",
            "irreversible or externally-visible action",
            "Gate 2 — size",
            "200 lines or more",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.claude_md)

    def test_ambiguous_gate_one_defaults_to_not_offering(self):
        # Negative-pin rationale: inverting the old exclusion list into a
        # positive "offer if..." condition invites the model to read its own
        # plan as containing a "design decision" by default, reproducing the
        # old near-every-plan dialog frequency. Without an explicit
        # ambiguity-defaults-to-skip rule, ambiguity resolves toward showing
        # the dialog rather than away from it.
        self.assertIn(
            "When it is unclear whether gate 1 holds, treat it as unmet",
            self.claude_md,
        )

    def test_four_dialog_options_are_intact(self):
        for required in (
            "Both: open the browser and also run the deep-dive.",
            "Deep-dive only: run grilling then dig without opening the browser.",
            "Open the browser now, decide on the deep-dive after reading.",
            "Neither.",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.claude_md)

    def test_deep_dive_is_offered_as_an_indivisible_pair(self):
        # Negative-pin rationale: the user chose "both or neither" over a
        # per-skill menu, because grilling settles decisions and dig stresses
        # them — either half alone leaves the plan half-reviewed. Listing them
        # as separate options would silently restore the split the user
        # rejected, so the prohibition must stay explicit in the prompt.
        for required in (
            "never list grilling and dig as separate selectable options",
            "fixed two-stage pair, never one half alone",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.claude_md)

    def test_grilling_runs_before_dig_and_never_concurrently(self):
        for required in (
            "invoke the `grilling` skill and complete its rounds",
            "then invoke the `dig` skill on the plan grilling produced",
            "Never start dig while grilling still has open questions",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.claude_md)

    def test_grilling_is_pinned_inline_rather_than_forked(self):
        # Negative-pin rationale: dig is a forked subagent, so a later edit
        # aligning the two stages could fork grilling too. A forked agent has
        # no AskUserQuestion, which would make grilling's interview — its
        # entire purpose — invisible to the user.
        self.assertIn(
            "grilling always runs inline in the main session", self.claude_md
        )

    def test_plan_is_re_presented_once_after_the_pair_not_between_stages(self):
        self.assertIn("once, after dig, not between the two stages", self.claude_md)


if __name__ == "__main__":
    unittest.main()
