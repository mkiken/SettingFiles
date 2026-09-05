import unittest

from support import REPO_ROOT


CODEX_BASE_PATH = REPO_ROOT / "ai/codex/codex_base.md"
AGENTS_PATH = REPO_ROOT / "ai/codex/_AGENTS.md"


class PlanReviewCriteriaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.codex_base = CODEX_BASE_PATH.read_text(encoding="utf-8")
        cls.agents = AGENTS_PATH.read_text(encoding="utf-8")

    def test_skip_criterion_governs_both_offers(self):
        for required in (
            "governs both the deep-dive offer and the Plan Review Presentation browser offer",
            "the shared file's own line-count/format criteria do not apply here",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.codex_base)

    def test_two_gates_must_both_hold_before_offering(self):
        for required in (
            "offer both only when two gates both hold",
            "Gate 1 — content",
            "undecided design decision or trade-off",
            "spans 3+ files or crosses subsystem/module boundaries",
            "irreversible or externally-visible action",
            "Gate 2 — size",
            "200 lines or more",
            "skip straight to the final `<proposed_plan>` with no dialog",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.codex_base)

    def test_ambiguous_gate_one_defaults_to_not_offering(self):
        # Negative-pin rationale: inverting the old exclusion list into a
        # positive "offer if..." condition invites the model to read its own
        # plan as containing a "design decision" by default, reproducing the
        # old near-every-plan dialog frequency. Without an explicit
        # ambiguity-defaults-to-skip rule, ambiguity resolves toward showing
        # the dialog rather than away from it.
        self.assertIn("When it is unclear whether gate 1 holds, treat it as unmet", self.codex_base)

    def test_complete_terminal_preview_precedes_review_choice(self):
        preview_instruction = "first output a terminal review preview"
        choice_instruction = "Only after the full preview is visible, present this question"

        self.assertIn(preview_instruction, self.codex_base)
        self.assertIn(choice_instruction, self.codex_base)
        self.assertLess(
            self.codex_base.index(preview_instruction),
            self.codex_base.index(choice_instruction),
        )
        for required in (
            "complete decision-complete plan exactly as it would appear inside `<proposed_plan>`",
            "without the protocol tags",
            "Do not replace it with a summary or partial update",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.codex_base)

    def test_four_option_review_choice_is_always_plain_text(self):
        plan_review = self.codex_base.split("# Plan Review Deep-Dive (grilling → dig)", 1)[1]

        for required in (
            "plain-text Markdown ordered list",
            "never call `request_user_input` for it",
            "four authored options exceed the runtime limit",
            "Treat a number-only reply as selecting the corresponding option",
            "1. Both: open the browser and also run the deep-dive.",
            "2. Deep-dive only: run grilling then dig without opening the browser.",
            "3. Open the browser now, decide on the deep-dive after reading.",
            "4. Neither.",
        ):
            with self.subTest(required=required):
                self.assertIn(required, plan_review)

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
                self.assertIn(required, self.codex_base)

    def test_grilling_runs_before_dig_and_never_concurrently(self):
        for required in (
            "load the `grilling` skill and complete its rounds",
            "then load the `dig` skill on the plan grilling produced",
            "Never start dig while grilling still has open questions",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.codex_base)

    def test_preview_repeats_once_after_the_pair_not_between_stages(self):
        self.assertIn("once, after dig, not between the two stages", self.codex_base)

    def test_neither_finalizes_the_preview_and_dig_repeats_the_flow(self):
        for required in (
            "If option 4 is chosen, output the previewed plan unchanged",
            "repeat the full terminal preview and review-choice flow with the revised plan",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.codex_base)

    def test_codex_has_no_plan_file_and_uses_an_ephemeral_browser_path(self):
        for required in (
            "Codex has no `~/.codex/plans`;",
            "Never use Claude-only port 4649/`~/.claude/plans`.",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.codex_base)
        # ~/.codex/plans does not exist; referencing it as a real target would
        # regress toward the Claude-only plan-file persistence model.
        self.assertNotIn("mounting `~/.codex/plans`", self.codex_base)

    def test_generated_agents_md_carries_the_same_criteria(self):
        for required in (
            "governs both the deep-dive offer and the Plan Review Presentation browser offer",
            "Codex has no `~/.codex/plans`;",
            "first output a terminal review preview",
            "offer both only when two gates both hold",
            "200 lines or more",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.agents)


if __name__ == "__main__":
    unittest.main()
