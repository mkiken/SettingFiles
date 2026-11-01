import unittest

from support import REPO_ROOT


MODELS = REPO_ROOT / "ai/common/skills/second-opinion/references/models.md"


class SecondOpinionModelsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = MODELS.read_text(encoding="utf-8")

    def test_every_target_has_model_candidates(self):
        for row_start in ("| codex |", "| claude |", "| gemini |"):
            with self.subTest(row_start=row_start):
                self.assertIn(row_start, self.text)

    def test_gemini_effort_is_marked_unsettable(self):
        gemini_row = next(line for line in self.text.splitlines() if line.startswith("| gemini |"))
        self.assertIn("not settable", gemini_row)

    def test_gemini_is_marked_unverified(self):
        self.assertIn("Gemini is unverified", self.text)

    def test_difficulty_defaults_name_a_model_and_effort_per_target(self):
        for required in ("`gpt-6.1-sol` + `medium`", "`opus` + `high`", "`flash`", "`pro`"):
            with self.subTest(required=required):
                self.assertIn(required, self.text)


if __name__ == "__main__":
    unittest.main()
