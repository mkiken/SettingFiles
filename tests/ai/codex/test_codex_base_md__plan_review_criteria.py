import unittest

from support import REPO_ROOT


CODEX_BASE_PATH = REPO_ROOT / "ai/codex/codex_base.md"
AGENTS_PATH = REPO_ROOT / "ai/codex/_AGENTS.md"
REFERENCE_PATH = (
    REPO_ROOT / "ai/common/skills/plan-review/references/codex.md"
)


class PlanReviewCriteriaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.codex_base = " ".join(CODEX_BASE_PATH.read_text(encoding="utf-8").split())
        cls.agents = " ".join(AGENTS_PATH.read_text(encoding="utf-8").split())
        cls.reference = " ".join(REFERENCE_PATH.read_text(encoding="utf-8").split())

    def test_always_on_layer_keeps_only_the_review_gate(self):
        for required in (
            "load the `plan-review` skill only when",
            "both gates hold",
            "Gate 1 — content",
            "spans 3+ files or subsystem/module boundaries",
            "Treat ambiguity as",
            "Gate 2 — size",
            "at least 200 lines",
            "with no review dialog",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.codex_base)

        self.assertNotIn(
            "1. Both: open the browser and also run the deep-dive.",
            self.codex_base,
        )
        self.assertNotIn("mdv -d -n -q", self.codex_base)

    def test_reference_preserves_preview_before_the_choice(self):
        preview = "First output the complete decision-complete plan"
        choice = "Only after the full preview is visible"
        self.assertLess(self.reference.index(preview), self.reference.index(choice))
        self.assertIn("without the protocol tags", self.reference)
        self.assertIn("summary or partial update", self.reference)

    def test_reference_preserves_all_four_actions(self):
        for required in (
            "1. Both: open the browser and also run the deep-dive.",
            "2. Deep-dive only: run grilling then dig without opening the browser.",
            "3. Open the browser now, decide on the deep-dive after reading.",
            "4. Neither.",
            "Do not call `request_user_input`",
            "Never offer grilling and dig separately",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.reference)

    def test_reference_orders_grilling_before_dig(self):
        grilling = "complete grilling until its frontier is empty"
        dig = "only then run dig"
        self.assertLess(self.reference.index(grilling), self.reference.index(dig))
        self.assertIn("once, after dig and not between", self.reference)

    def test_codex_browser_flow_uses_only_a_scratchpad(self):
        self.assertIn("Codex has no `~/.codex/plans`", self.reference)
        self.assertIn("session-owned scratchpad directory", self.reference)
        self.assertIn("Never use Claude's port 4649", self.reference)
        self.assertNotIn("mounting `~/.codex/plans`", self.reference)

    def test_generated_agents_keeps_the_conditional_pointer(self):
        for required in (
            "load the `plan-review` skill only when",
            "both gates hold",
            "at least 200 lines",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.agents)


if __name__ == "__main__":
    unittest.main()
