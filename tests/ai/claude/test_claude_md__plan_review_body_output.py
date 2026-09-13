import unittest

from support import REPO_ROOT


CLAUDE_MD_PATH = REPO_ROOT / "ai/claude/_CLAUDE.md"
REFERENCE_PATH = (
    REPO_ROOT / "ai/common/skills/plan-review/references/claude.md"
)


class PlanReviewBodyOutputTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.claude_md = " ".join(CLAUDE_MD_PATH.read_text(encoding="utf-8").split())
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
            "proceed directly to `ExitPlanMode`",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.claude_md)

        self.assertNotIn(
            "Both: open the browser and also run the deep-dive.",
            self.claude_md,
        )
        self.assertNotIn("mdv -d -n -q", self.claude_md)

    def test_reference_outputs_the_full_plan_before_the_dialog(self):
        plan = "Output the plan file's complete current content"
        question = "Use one single-select `AskUserQuestion`"
        self.assertLess(self.reference.index(plan), self.reference.index(question))
        self.assertIn("without a code fence or summary", self.reference)
        self.assertIn("later `ExitPlanMode` rendering is intentionally separate", self.reference)

    def test_reference_preserves_all_four_actions(self):
        for required in (
            "Both: open the browser and also run the deep-dive.",
            "Deep-dive only: run grilling then dig without opening the browser.",
            "Open the browser now, decide on the deep-dive after reading.",
            "Neither.",
            "Never offer grilling and dig separately",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.reference)

    def test_reference_keeps_interview_and_server_lifecycle(self):
        for required in (
            "Complete grilling until its frontier is empty",
            "only then run dig",
            "Grilling runs inline",
            "never stop the persistent port-4649 viewer",
            "after dig and not between stages",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.reference)

    def test_reference_preserves_claude_plan_server(self):
        for required in (
            "~/.claude/plans",
            "http://127.0.0.1:4649/__mdv/assets/mdv.css",
            "mdv -d -n -q -p 4649 ~/.claude/plans",
            "Never stop the true port-4649 server",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.reference)


if __name__ == "__main__":
    unittest.main()
