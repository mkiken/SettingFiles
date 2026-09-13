import unittest

from support import REPO_ROOT


PATH = REPO_ROOT / "ai/common/skills/plan-review/references/claude.md"


class ClaudeReviewFlowTest(unittest.TestCase):
    def test_keeps_persistent_plan_server_and_inline_interview(self):
        content = " ".join(PATH.read_text(encoding="utf-8").split())
        self.assertIn("Grilling runs inline", content)
        self.assertIn("~/.claude/plans", content)
        self.assertIn("Never stop the true port-4649 server", content)


if __name__ == "__main__":
    unittest.main()
