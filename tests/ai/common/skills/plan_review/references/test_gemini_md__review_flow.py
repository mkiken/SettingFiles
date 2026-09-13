import unittest

from support import REPO_ROOT


PATH = REPO_ROOT / "ai/common/skills/plan-review/references/gemini.md"


class GeminiReviewFlowTest(unittest.TestCase):
    def test_uses_platform_confirmation_and_failsafe_scratchpad(self):
        content = " ".join(PATH.read_text(encoding="utf-8").split())
        self.assertIn("Gemini's user-confirmation mechanism", content)
        self.assertIn("session-owned scratchpad directory", content)
        self.assertIn("Wait for the user to finish", content)


if __name__ == "__main__":
    unittest.main()
