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
            "governs both the `dig` skill offer and the Plan Review Presentation browser offer",
            "the shared file's own line-count/format criteria do not apply here",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.codex_base)

    def test_mechanical_plans_skip_both_offers(self):
        for required in (
            "renames, bulk replacements, reverts, single-file fixes with no design decision",
            "plans whose every task is a stated verbatim edit",
            "skip both offers",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.codex_base)

    def test_complete_terminal_preview_precedes_review_choice(self):
        preview_instruction = "first output a terminal review preview"
        choice_instruction = "Only after the full preview is visible, offer a single choice"

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

    def test_neither_finalizes_the_preview_and_dig_repeats_the_flow(self):
        for required in (
            "If option 4 is chosen, output the previewed plan unchanged",
            "repeat the full terminal preview and review-choice flow with the revised plan",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.codex_base)

    def test_codex_has_no_plan_file_and_uses_an_ephemeral_browser_path(self):
        for required in (
            "Codex has no `~/.codex/plans` directory",
            "Do not reuse the fixed port 8600 / `~/.claude/plans` mount",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.codex_base)
        # ~/.codex/plans does not exist; referencing it as a real target would
        # regress toward the Claude-only plan-file persistence model.
        self.assertNotIn("mounting `~/.codex/plans`", self.codex_base)

    def test_generated_agents_md_carries_the_same_criteria(self):
        for required in (
            "governs both the `dig` skill offer and the Plan Review Presentation browser offer",
            "Codex has no `~/.codex/plans` directory",
            "first output a terminal review preview",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.agents)


if __name__ == "__main__":
    unittest.main()
