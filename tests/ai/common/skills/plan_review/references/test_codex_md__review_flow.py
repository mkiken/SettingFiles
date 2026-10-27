import unittest

from support import REPO_ROOT


PATH = REPO_ROOT / "ai/common/skills/plan-review/references/codex.md"


class CodexReviewFlowTest(unittest.TestCase):
    def test_four_choices_use_the_shared_ui_or_single_numbered_fallback(self):
        content = " ".join(PATH.read_text(encoding="utf-8").split())
        self.assertIn("always-on `# User Confirmation` rules", content)
        self.assertIn("Use a choice UI if all four fit", content)
        self.assertIn("otherwise present them together as a numbered list", content)

    def test_uses_four_choices_and_ephemeral_scratchpad(self):
        content = " ".join(PATH.read_text(encoding="utf-8").split())
        self.assertEqual(content.count("1. Both:"), 1)
        self.assertIn("4. Neither.", content)
        self.assertIn("session-owned scratchpad directory", content)
        self.assertIn("Never use Claude's port 4649", content)


if __name__ == "__main__":
    unittest.main()
