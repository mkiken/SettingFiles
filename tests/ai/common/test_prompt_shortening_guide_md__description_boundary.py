import unittest

from support import REPO_ROOT


GUIDE_PATH = REPO_ROOT / "ai/common/prompt_shortening_guide.md"


class PromptShorteningDescriptionBoundaryTest(unittest.TestCase):
    def test_meaning_preserving_shortening_does_not_redesign_discovery(self):
        content = GUIDE_PATH.read_text(encoding="utf-8")
        self.assertIn("preserves discovery behavior", content)
        self.assertIn("separate prompt-improvement task", content)
        self.assertIn("intended/confusable-request validation", content)


if __name__ == "__main__":
    unittest.main()
