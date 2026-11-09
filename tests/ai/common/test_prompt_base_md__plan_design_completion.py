import unittest

from support import REPO_ROOT


class PlanDesignCompletionContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        content = (REPO_ROOT / "ai/common/prompt_base.md").read_text(encoding="utf-8")
        cls.content = content

    def test_material_decisions_are_resolved_before_approval(self):
        for requirement in (
            "Before requesting plan approval, resolve all material design decisions",
            "scope, behavior, public interfaces, data formats, failure handling, and test conditions with expected outcomes",
            "Investigate what can be learned first and ask the user about unresolved decisions during planning",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, self.content)

    def test_decisions_are_recorded_for_implementation(self):
        self.assertIn(
            "Record the decisions in the plan so another implementer can proceed without additional material design choices",
            self.content,
        )

    def test_implementation_retains_local_discretion(self):
        self.assertIn(
            "After approval, implement and verify the plan; leave behavior-preserving local naming and coding choices to the implementer",
            self.content,
        )

    def test_new_facts_requiring_design_change_pause_affected_work(self):
        self.assertIn(
            "If new facts require a design change, stop affected work, confirm only that decision with the user, update the plan, and continue; whole-plan reapproval is not mandatory",
            self.content,
        )


if __name__ == "__main__":
    unittest.main()
