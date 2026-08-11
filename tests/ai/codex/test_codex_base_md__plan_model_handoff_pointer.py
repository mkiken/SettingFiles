import unittest

from support import REPO_ROOT


CODEX_BASE_PATH = REPO_ROOT / "ai/codex/codex_base.md"


class PlanModelHandoffPointerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.codex_base = CODEX_BASE_PATH.read_text(encoding="utf-8")

    def test_handoff_checkpoints_load_the_skill(self):
        self.assertIn("finalizing a plan in Plan Mode", self.codex_base)
        self.assertIn("starting implementation of an accepted plan", self.codex_base)
        self.assertIn("load the `plan-model-handoff` skill", self.codex_base)
        self.assertIn("before emitting the final plan", self.codex_base)
        self.assertIn("causing the first implementation side effect", self.codex_base)

    def test_procedure_stays_out_of_the_always_on_prompt(self):
        # Detection details belong in the skill so the always-on prompt stays
        # lean and cannot drift from a duplicated procedure.
        for detail in ("CODEX_THREAD_ID", ".codex/sessions", "turn_context"):
            with self.subTest(detail=detail):
                self.assertNotIn(detail, self.codex_base)


if __name__ == "__main__":
    unittest.main()
