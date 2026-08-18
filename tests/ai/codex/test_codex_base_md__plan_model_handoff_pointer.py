import unittest

from support import REPO_ROOT


CODEX_BASE_PATH = REPO_ROOT / "ai/codex/codex_base.md"


class PlanModelHandoffPointerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.codex_base = CODEX_BASE_PATH.read_text(encoding="utf-8")

    def test_accepted_plan_implementation_checkpoint_loads_the_skill(self):
        pointer = next(
            line
            for line in self.codex_base.splitlines()
            if "load the `plan-model-handoff` skill" in line
        )
        self.assertIn("starting implementation of an accepted plan", pointer)
        self.assertIn("immediately before the first implementation side effect", pointer)

        # Exclusions keep the handoff after the complete plan is visible, so the
        # user can inspect it before choosing an implementation model.
        for excluded in ("finalizing a plan in Plan Mode", "before emitting the final plan"):
            with self.subTest(excluded=excluded):
                self.assertNotIn(excluded, pointer)

    def test_procedure_stays_out_of_the_always_on_prompt(self):
        # Detection details belong in the skill so the always-on prompt stays
        # lean and cannot drift from a duplicated procedure.
        for detail in ("CODEX_THREAD_ID", ".codex/sessions", "turn_context"):
            with self.subTest(detail=detail):
                self.assertNotIn(detail, self.codex_base)


if __name__ == "__main__":
    unittest.main()
